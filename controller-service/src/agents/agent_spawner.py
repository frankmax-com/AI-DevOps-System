"""
Agent Spawner - Creates and Manages AI Agent Instances
Handles container orchestration, lifecycle management, and health monitoring
"""

import asyncio
import docker
import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
import json
import os
import yaml
from pathlib import Path
import aiohttp
import uuid

from ..models.agent_models import AgentSpec, AgentInstance, AgentStatus, AgentRole
from ..models.startup_spec import TenantResources
from ..core.token_manager import TokenManager
from .vault_client import VaultClient

logger = logging.getLogger(__name__)

class AgentSpawner:
    """Manages AI agent lifecycle - creation, monitoring, and termination"""
    
    def __init__(self, token_manager: TokenManager, vault_client: VaultClient):
        self.token_manager = token_manager
        self.vault_client = vault_client
        self.docker_client = docker.from_env()
        self.active_agents: Dict[str, AgentInstance] = {}
        self.monitoring_tasks: Dict[str, asyncio.Task] = {}
        
        # Agent service configurations
        self.agent_services = {
            AgentRole.GITHUB_BOOTSTRAP: {
                "image": "ai-devops/github-bootstrap:latest",
                "port": 8080,
                "cpu_limit": "1",
                "memory_limit": "1g"
            },
            AgentRole.FOUNDER: {
                "image": "ai-devops/founder-agent:latest", 
                "port": 8081,
                "cpu_limit": "2",
                "memory_limit": "2g"
            },
            AgentRole.DEVELOPER: {
                "image": "ai-devops/dev-agent:latest",
                "port": 8082,
                "cpu_limit": "4",
                "memory_limit": "4g"
            },
            AgentRole.DEVOPS: {
                "image": "ai-devops/devops-agent:latest",
                "port": 8083,
                "cpu_limit": "2",
                "memory_limit": "2g"
            },
            AgentRole.SECURITY: {
                "image": "ai-devops/security-agent:latest",
                "port": 8084,
                "cpu_limit": "2",
                "memory_limit": "2g"
            },
            AgentRole.QA: {
                "image": "ai-devops/qa-agent:latest",
                "port": 8085,
                "cpu_limit": "2",
                "memory_limit": "2g"
            },
            AgentRole.RELEASE: {
                "image": "ai-devops/release-agent:latest",
                "port": 8086,
                "cpu_limit": "1",
                "memory_limit": "1g"
            },
            AgentRole.PM: {
                "image": "ai-devops/pm-agent:latest",
                "port": 8087,
                "cpu_limit": "1",
                "memory_limit": "1g"
            },
            AgentRole.AUDIT: {
                "image": "ai-devops/audit-agent:latest",
                "port": 8088,
                "cpu_limit": "1",
                "memory_limit": "1g"
            }
        }
    
    async def spawn_agent(self, spec: AgentSpec, 
                         tenant_resources: TenantResources) -> AgentInstance:
        """
        Spawn a new AI agent with proper isolation and security
        
        Args:
            spec: Agent specification
            tenant_resources: Tenant-specific resources and boundaries
            
        Returns:
            Running agent instance
        """
        logger.info(f"Spawning agent {spec.agent_id} for startup {spec.startup_id}")
        
        try:
            # Generate ephemeral token for the agent
            token_data = await self.token_manager.issue_token(
                tenant_id=spec.startup_id,
                scopes=spec.scopes,
                ttl_hours=8,  # 8-hour maximum runtime
                metadata={
                    "agent_id": spec.agent_id,
                    "role": spec.role.value,
                    "created_for": "agent_spawn"
                }
            )
            
            # Create agent instance record
            instance = AgentInstance(
                agent_id=spec.agent_id,
                startup_id=spec.startup_id,
                role=spec.role,
                status=AgentStatus.SPAWNING,
                access_token=token_data["access_token"],
                token_expires_at=datetime.fromisoformat(token_data["expires_at"]),
                spec=spec
            )
            
            # Get tenant encryption key
            encryption_key = await self.vault_client.get_tenant_encryption_key(spec.startup_id)
            
            # Prepare container configuration
            container_config = await self._prepare_container_config(
                spec, tenant_resources, token_data["access_token"], encryption_key
            )
            
            # Create and start container
            container = self._create_container(container_config)
            container.start()
            
            # Update instance with container details
            instance.container_id = container.id
            instance.status = AgentStatus.ACTIVE
            instance.started_at = datetime.utcnow()
            
            # Set up agent endpoint
            service_config = self.agent_services[spec.role]
            instance.endpoint_url = f"http://localhost:{service_config['port']}"
            
            # Store active agent
            self.active_agents[spec.agent_id] = instance
            
            # Start monitoring task
            self.monitoring_tasks[spec.agent_id] = asyncio.create_task(
                self._monitor_agent(instance)
            )
            
            logger.info(f"Successfully spawned agent {spec.agent_id}")
            return instance
            
        except Exception as e:
            logger.error(f"Failed to spawn agent {spec.agent_id}: {e}")
            if spec.agent_id in self.active_agents:
                del self.active_agents[spec.agent_id]
            raise
    
    async def terminate_agent(self, agent_id: str, reason: str = "manual") -> bool:
        """
        Terminate an agent and clean up resources
        
        Args:
            agent_id: Agent identifier
            reason: Termination reason
            
        Returns:
            True if successful
        """
        logger.info(f"Terminating agent {agent_id}, reason: {reason}")
        
        if agent_id not in self.active_agents:
            logger.warning(f"Agent {agent_id} not found in active agents")
            return False
        
        instance = self.active_agents[agent_id]
        
        try:
            # Update status
            instance.status = AgentStatus.TERMINATING
            instance.terminated_at = datetime.utcnow()
            
            # Stop monitoring
            if agent_id in self.monitoring_tasks:
                self.monitoring_tasks[agent_id].cancel()
                del self.monitoring_tasks[agent_id]
            
            # Revoke agent token
            if instance.access_token:
                await self.token_manager.revoke_token(
                    instance.access_token,
                    reason=f"agent_termination: {reason}"
                )
            
            # Stop and remove container
            if instance.container_id:
                try:
                    container = self.docker_client.containers.get(instance.container_id)
                    container.stop(timeout=30)
                    container.remove()
                    logger.debug(f"Container {instance.container_id} stopped and removed")
                except docker.errors.NotFound:
                    logger.warning(f"Container {instance.container_id} not found")
                except Exception as e:
                    logger.error(f"Error stopping container {instance.container_id}: {e}")
            
            # Update final status
            instance.status = AgentStatus.TERMINATED
            
            # Remove from active agents
            del self.active_agents[agent_id]
            
            logger.info(f"Successfully terminated agent {agent_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error terminating agent {agent_id}: {e}")
            instance.status = AgentStatus.ERROR
            instance.error_message = str(e)
            return False
    
    async def get_agent_status(self, agent_id: str) -> Optional[AgentInstance]:
        """Get current status of an agent"""
        return self.active_agents.get(agent_id)
    
    async def list_active_agents(self, startup_id: Optional[str] = None) -> List[AgentInstance]:
        """List all active agents, optionally filtered by startup"""
        agents = list(self.active_agents.values())
        
        if startup_id:
            agents = [agent for agent in agents if agent.startup_id == startup_id]
        
        return agents
    
    async def suspend_agent(self, agent_id: str, reason: str = "manual") -> bool:
        """Suspend an agent (pause container)"""
        if agent_id not in self.active_agents:
            return False
        
        instance = self.active_agents[agent_id]
        
        try:
            if instance.container_id:
                container = self.docker_client.containers.get(instance.container_id)
                container.pause()
                
                instance.status = AgentStatus.SUSPENDED
                logger.info(f"Suspended agent {agent_id}, reason: {reason}")
                return True
                
        except Exception as e:
            logger.error(f"Error suspending agent {agent_id}: {e}")
            instance.error_message = str(e)
        
        return False
    
    async def resume_agent(self, agent_id: str) -> bool:
        """Resume a suspended agent"""
        if agent_id not in self.active_agents:
            return False
        
        instance = self.active_agents[agent_id]
        
        try:
            if instance.container_id and instance.status == AgentStatus.SUSPENDED:
                container = self.docker_client.containers.get(instance.container_id)
                container.unpause()
                
                instance.status = AgentStatus.ACTIVE
                instance.last_activity = datetime.utcnow()
                logger.info(f"Resumed agent {agent_id}")
                return True
                
        except Exception as e:
            logger.error(f"Error resuming agent {agent_id}: {e}")
            instance.error_message = str(e)
        
        return False
    
    async def _prepare_container_config(self, spec: AgentSpec, 
                                      tenant_resources: TenantResources,
                                      access_token: str,
                                      encryption_key: str) -> Dict[str, Any]:
        """Prepare Docker container configuration"""
        service_config = self.agent_services[spec.role]
        
        # Environment variables
        env_vars = {
            "AGENT_ID": spec.agent_id,
            "STARTUP_ID": spec.startup_id,
            "AGENT_ROLE": spec.role.value,
            "ACCESS_TOKEN": access_token,
            "ENCRYPTION_KEY": encryption_key,
            "TENANT_PREFIX": tenant_resources.resource_prefix,
            "KEY_VAULT_NAME": tenant_resources.key_vault_name,
            # Governance factory endpoints
            "GITHUB_GOVERNANCE_URL": os.getenv("GITHUB_GOVERNANCE_URL", "http://host.docker.internal:8001"),
            "AZURE_GOVERNANCE_URL": os.getenv("AZURE_GOVERNANCE_URL", "http://host.docker.internal:8002"),
            "AI_PROVIDER_GOVERNANCE_URL": os.getenv("AI_PROVIDER_GOVERNANCE_URL", "http://host.docker.internal:8003"),
            "DATABASE_GOVERNANCE_URL": os.getenv("DATABASE_GOVERNANCE_URL", "http://host.docker.internal:8004"),
            # Controller service endpoint
            "CONTROLLER_SERVICE_URL": os.getenv("CONTROLLER_SERVICE_URL", "http://host.docker.internal:8000"),
            **spec.environment_variables
        }
        
        # Resource limits
        resource_config = {
            "cpu_limit": spec.cpu_limit,
            "mem_limit": spec.memory_limit,
            "memswap_limit": spec.memory_limit,  # Disable swap
            "oom_kill_disable": False
        }
        
        # Network configuration (isolated per tenant)
        network_name = f"tenant-{spec.startup_id}-network"
        
        # Security configuration
        security_opts = [
            "no-new-privileges:true",
            "apparmor:docker-default"
        ]
        
        return {
            "image": service_config["image"],
            "name": f"agent-{spec.agent_id}",
            "environment": env_vars,
            "ports": {f"{service_config['port']}/tcp": service_config['port']},
            "labels": {
                "agent_id": spec.agent_id,
                "startup_id": spec.startup_id,
                "role": spec.role.value,
                "managed_by": "controller-service"
            },
            "network": network_name,
            "security_opt": security_opts,
            "read_only": True,
            "tmpfs": {"/tmp": "noexec,nosuid,size=1g"},
            "user": "1000:1000",  # Non-root user
            **resource_config
        }
    
    def _create_container(self, config: Dict[str, Any]) -> docker.models.containers.Container:
        """Create Docker container with configuration"""
        try:
            # Ensure network exists
            network_name = config.pop("network")
            self._ensure_network_exists(network_name)
            
            # Create container
            container = self.docker_client.containers.create(**config)
            
            # Connect to tenant network
            network = self.docker_client.networks.get(network_name)
            network.connect(container)
            
            return container
            
        except Exception as e:
            logger.error(f"Error creating container: {e}")
            raise
    
    def _ensure_network_exists(self, network_name: str):
        """Ensure Docker network exists for tenant isolation"""
        try:
            self.docker_client.networks.get(network_name)
        except docker.errors.NotFound:
            logger.info(f"Creating tenant network: {network_name}")
            self.docker_client.networks.create(
                name=network_name,
                driver="bridge",
                options={
                    "com.docker.network.bridge.enable_icc": "true",
                    "com.docker.network.bridge.enable_ip_masquerade": "true"
                },
                labels={"purpose": "tenant-isolation"}
            )
    
    async def _monitor_agent(self, instance: AgentInstance):
        """Monitor agent health and resource usage"""
        agent_id = instance.agent_id
        logger.debug(f"Starting monitoring for agent {agent_id}")
        
        try:
            while instance.status in [AgentStatus.ACTIVE, AgentStatus.IDLE, AgentStatus.BUSY]:
                await asyncio.sleep(30)  # Check every 30 seconds
                
                # Check if agent should be terminated due to runtime limits
                if instance.should_terminate():
                    logger.warning(f"Agent {agent_id} exceeded maximum runtime, terminating")
                    await self.terminate_agent(agent_id, "runtime_limit_exceeded")
                    break
                
                # Check token expiration
                if instance.is_expired():
                    logger.warning(f"Agent {agent_id} token expired, terminating")
                    await self.terminate_agent(agent_id, "token_expired")
                    break
                
                # Update resource usage
                if instance.container_id:
                    try:
                        container = self.docker_client.containers.get(instance.container_id)
                        stats = container.stats(stream=False)
                        
                        # Calculate CPU usage percentage
                        cpu_usage = self._calculate_cpu_usage(stats)
                        instance.cpu_usage = cpu_usage
                        
                        # Calculate memory usage percentage
                        memory_usage = self._calculate_memory_usage(stats)
                        instance.memory_usage = memory_usage
                        
                        # Check health endpoint
                        health_status = await self._check_agent_health(instance)
                        instance.health_status = health_status
                        
                        # Update activity status
                        if cpu_usage > 10 or memory_usage > 50:
                            instance.status = AgentStatus.BUSY
                            instance.last_activity = datetime.utcnow()
                        elif instance.status == AgentStatus.BUSY:
                            instance.status = AgentStatus.IDLE
                        
                        # Check for idle timeout
                        if (instance.last_activity and 
                            datetime.utcnow() - instance.last_activity > instance.spec.max_idle_duration):
                            logger.info(f"Agent {agent_id} idle timeout, suspending")
                            await self.suspend_agent(agent_id, "idle_timeout")
                        
                    except docker.errors.NotFound:
                        logger.warning(f"Container for agent {agent_id} not found")
                        instance.status = AgentStatus.ERROR
                        instance.error_message = "Container not found"
                        break
                    except Exception as e:
                        logger.error(f"Error monitoring agent {agent_id}: {e}")
                        instance.error_message = str(e)
                
        except asyncio.CancelledError:
            logger.debug(f"Monitoring cancelled for agent {agent_id}")
        except Exception as e:
            logger.error(f"Monitoring error for agent {agent_id}: {e}")
            instance.status = AgentStatus.ERROR
            instance.error_message = str(e)
    
    def _calculate_cpu_usage(self, stats: Dict) -> float:
        """Calculate CPU usage percentage from Docker stats"""
        try:
            cpu_stats = stats["cpu_stats"]
            precpu_stats = stats["precpu_stats"]
            
            cpu_delta = cpu_stats["cpu_usage"]["total_usage"] - precpu_stats["cpu_usage"]["total_usage"]
            system_delta = cpu_stats["system_cpu_usage"] - precpu_stats["system_cpu_usage"]
            
            if system_delta > 0:
                cpu_usage = (cpu_delta / system_delta) * len(cpu_stats["cpu_usage"]["percpu_usage"]) * 100
                return round(cpu_usage, 2)
            
        except (KeyError, ZeroDivisionError):
            pass
        
        return 0.0
    
    def _calculate_memory_usage(self, stats: Dict) -> float:
        """Calculate memory usage percentage from Docker stats"""
        try:
            memory_stats = stats["memory_stats"]
            usage = memory_stats["usage"]
            limit = memory_stats["limit"]
            
            if limit > 0:
                memory_usage = (usage / limit) * 100
                return round(memory_usage, 2)
            
        except KeyError:
            pass
        
        return 0.0
    
    async def _check_agent_health(self, instance: AgentInstance) -> str:
        """Check agent health via HTTP endpoint"""
        if not instance.endpoint_url:
            return "unknown"
        
        try:
            timeout = aiohttp.ClientTimeout(total=5)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                health_url = f"{instance.endpoint_url}/health"
                headers = {"Authorization": f"Bearer {instance.access_token}"}
                
                async with session.get(health_url, headers=headers) as response:
                    if response.status == 200:
                        return "healthy"
                    else:
                        return f"unhealthy ({response.status})"
                        
        except Exception:
            return "unreachable"
    
    async def cleanup_orphaned_containers(self):
        """Clean up orphaned agent containers"""
        try:
            containers = self.docker_client.containers.list(
                filters={"label": "managed_by=controller-service"}
            )
            
            cleaned_count = 0
            for container in containers:
                agent_id = container.labels.get("agent_id")
                if agent_id and agent_id not in self.active_agents:
                    logger.info(f"Cleaning up orphaned container for agent {agent_id}")
                    container.stop(timeout=10)
                    container.remove()
                    cleaned_count += 1
            
            logger.info(f"Cleaned up {cleaned_count} orphaned containers")
            return cleaned_count
            
        except Exception as e:
            logger.error(f"Error during container cleanup: {e}")
            return 0
    
    async def get_system_metrics(self) -> Dict[str, Any]:
        """Get system-wide agent metrics"""
        total_agents = len(self.active_agents)
        agents_by_role = {}
        agents_by_status = {}
        total_cpu = 0.0
        total_memory = 0.0
        
        for instance in self.active_agents.values():
            # Count by role
            role = instance.role.value
            agents_by_role[role] = agents_by_role.get(role, 0) + 1
            
            # Count by status
            status = instance.status.value
            agents_by_status[status] = agents_by_status.get(status, 0) + 1
            
            # Aggregate resource usage
            total_cpu += instance.cpu_usage
            total_memory += instance.memory_usage
        
        return {
            "total_agents": total_agents,
            "agents_by_role": agents_by_role,
            "agents_by_status": agents_by_status,
            "resource_usage": {
                "total_cpu_usage": round(total_cpu, 2),
                "total_memory_usage": round(total_memory, 2),
                "average_cpu_per_agent": round(total_cpu / max(total_agents, 1), 2),
                "average_memory_per_agent": round(total_memory / max(total_agents, 1), 2)
            },
            "monitoring_tasks_active": len(self.monitoring_tasks),
            "checked_at": datetime.utcnow().isoformat()
        }
