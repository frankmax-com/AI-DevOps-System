"""
Core Controller Engine - Orchestrates autonomous agent operations
"""

from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import asyncio
import structlog
import uuid

from ..models.startup_spec import StartupSpec
from ..models.agent_models import AgentSpawnRequest, AgentStatus
from ..agents.agent_spawner import AgentSpawner
from ..core.token_manager import TokenManager
from ..core.audit_manager import AuditManager
from ..integrations.governance_factories import GovernanceFactoryClient

logger = structlog.get_logger()

class ControllerEngine:
    """
    Core orchestration engine for autonomous AI agents
    Coordinates startup creation through agent workflows
    """
    
    def __init__(self):
        self.agent_spawner = AgentSpawner()
        self.token_manager = TokenManager()
        self.audit_manager = AuditManager()
        self.governance_client = GovernanceFactoryClient()
        self.active_startups: Dict[str, Dict[str, Any]] = {}
        self.agent_registry: Dict[str, AgentStatus] = {}
        
    async def initialize(self):
        """Initialize controller and all subsystems"""
        logger.info("Initializing Controller Engine")
        await self.governance_client.initialize()
        logger.info("Controller Engine initialized")
    
    async def orchestrate_startup_creation(self, startup_spec: StartupSpec) -> Dict[str, Any]:
        """
        Main orchestration workflow for autonomous startup creation
        Coordinates GitHub bootstrap → Agent spawning → Azure DevOps setup
        """
        startup_id = startup_spec.startup_id
        logger.info("Starting startup orchestration", startup_id=startup_id)
        
        try:
            # Initialize startup tracking
            self.active_startups[startup_id] = {
                "spec": startup_spec,
                "status": "orchestrating",
                "agents": {},
                "created_at": datetime.utcnow(),
                "phases": {
                    "github_bootstrap": "pending",
                    "founder_analysis": "pending", 
                    "azure_setup": "pending",
                    "team_agents": "pending",
                    "final_validation": "pending"
                }
            }
            
            # Phase 1: GitHub Bootstrap Agent
            logger.info("Phase 1: GitHub Bootstrap", startup_id=startup_id)
            github_result = await self._execute_github_bootstrap(startup_spec)
            self.active_startups[startup_id]["phases"]["github_bootstrap"] = "completed"
            self.active_startups[startup_id]["github_org"] = github_result["organization"]
            
            # Phase 2: Founder Agent Analysis
            logger.info("Phase 2: Founder Analysis", startup_id=startup_id)
            founder_result = await self._execute_founder_analysis(startup_spec)
            self.active_startups[startup_id]["phases"]["founder_analysis"] = "completed"
            self.active_startups[startup_id]["business_analysis"] = founder_result
            
            # Phase 3: Azure DevOps Setup
            logger.info("Phase 3: Azure DevOps Setup", startup_id=startup_id)
            azure_result = await self._execute_azure_devops_setup(startup_spec, founder_result)
            self.active_startups[startup_id]["phases"]["azure_setup"] = "completed"
            self.active_startups[startup_id]["azure_project"] = azure_result["project"]
            
            # Phase 4: Spawn Team Agents
            logger.info("Phase 4: Team Agents Spawning", startup_id=startup_id)
            team_result = await self._spawn_team_agents(startup_spec, founder_result)
            self.active_startups[startup_id]["phases"]["team_agents"] = "completed"
            self.active_startups[startup_id]["team_agents"] = team_result
            
            # Phase 5: Final Validation
            logger.info("Phase 5: Final Validation", startup_id=startup_id)
            validation_result = await self._execute_final_validation(startup_id)
            self.active_startups[startup_id]["phases"]["final_validation"] = "completed"
            
            # Mark startup as operational
            self.active_startups[startup_id]["status"] = "operational"
            self.active_startups[startup_id]["completed_at"] = datetime.utcnow()
            
            logger.info("Startup orchestration completed successfully", 
                       startup_id=startup_id,
                       completion_time=datetime.utcnow())
            
            return self.active_startups[startup_id]
            
        except Exception as e:
            logger.error("Startup orchestration failed", 
                        startup_id=startup_id, 
                        error=str(e))
            self.active_startups[startup_id]["status"] = "failed"
            self.active_startups[startup_id]["error"] = str(e)
            raise e
    
    async def _execute_github_bootstrap(self, startup_spec: StartupSpec) -> Dict[str, Any]:
        """Execute GitHub organization bootstrap through autonomous agent"""
        
        # Spawn GitHub Bootstrap Agent
        bootstrap_request = AgentSpawnRequest(
            agent_role="github_bootstrap",
            tenant_id=startup_spec.startup_id,
            capabilities=[
                "organization_creation",
                "repository_setup", 
                "team_management",
                "actions_configuration",
                "security_setup"
            ],
            context={
                "company_name": startup_spec.company_name,
                "founder_email": startup_spec.founder_email,
                "org_name": f"startup-{startup_spec.startup_id[:8]}"
            }
        )
        
        # Spawn and execute agent
        agent = await self.agent_spawner.spawn_agent(bootstrap_request)
        self.agent_registry[agent.agent_id] = agent
        
        # Agent executes GitHub operations through GitHub Governance Factory
        github_result = await self._execute_agent_workflow(
            agent.agent_id,
            "github_bootstrap_workflow",
            startup_spec
        )
        
        return github_result
    
    async def _execute_founder_analysis(self, startup_spec: StartupSpec) -> Dict[str, Any]:
        """Execute business analysis through Founder Agent"""
        
        # Spawn Founder Agent
        founder_request = AgentSpawnRequest(
            agent_role="founder",
            tenant_id=startup_spec.startup_id,
            capabilities=[
                "business_strategy_analysis",
                "market_research",
                "requirements_decomposition", 
                "epic_breakdown",
                "stakeholder_communication"
            ],
            context={
                "business_description": startup_spec.business_description,
                "industry": startup_spec.industry,
                "target_market": startup_spec.target_market,
                "funding_stage": startup_spec.funding_stage
            }
        )
        
        # Spawn and execute agent
        agent = await self.agent_spawner.spawn_agent(founder_request)
        self.agent_registry[agent.agent_id] = agent
        
        # Agent executes business analysis through AI Provider Factory
        founder_result = await self._execute_agent_workflow(
            agent.agent_id,
            "founder_analysis_workflow",
            startup_spec
        )
        
        return founder_result
    
    async def _execute_azure_devops_setup(
        self, 
        startup_spec: StartupSpec, 
        founder_analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute Azure DevOps project setup through Dev Agent"""
        
        # Spawn Dev Agent
        dev_request = AgentSpawnRequest(
            agent_role="dev",
            tenant_id=startup_spec.startup_id,
            capabilities=[
                "project_creation",
                "repository_setup",
                "pipeline_configuration",
                "work_item_hierarchy",
                "service_connections"
            ],
            context={
                "project_name": f"startup-{startup_spec.startup_id[:8]}",
                "epic_breakdown": founder_analysis.get("epic_breakdown", []),
                "technical_requirements": founder_analysis.get("technical_requirements", {})
            }
        )
        
        # Spawn and execute agent
        agent = await self.agent_spawner.spawn_agent(dev_request)
        self.agent_registry[agent.agent_id] = agent
        
        # Agent executes Azure DevOps setup through Azure DevOps Governance Factory
        azure_result = await self._execute_agent_workflow(
            agent.agent_id,
            "azure_devops_setup_workflow",
            startup_spec
        )
        
        return azure_result
    
    async def _spawn_team_agents(
        self, 
        startup_spec: StartupSpec,
        founder_analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Spawn remaining team agents (Ops, Security, Finance)"""
        
        team_agents = {}
        
        # Spawn Ops Agent
        ops_request = AgentSpawnRequest(
            agent_role="ops",
            tenant_id=startup_spec.startup_id,
            capabilities=[
                "infrastructure_planning",
                "deployment_automation",
                "monitoring_setup",
                "scaling_strategy"
            ],
            context={
                "infrastructure_requirements": founder_analysis.get("infrastructure_needs", {}),
                "deployment_strategy": "cloud_native"
            }
        )
        ops_agent = await self.agent_spawner.spawn_agent(ops_request)
        team_agents["ops"] = ops_agent
        self.agent_registry[ops_agent.agent_id] = ops_agent
        
        # Spawn Security Agent
        security_request = AgentSpawnRequest(
            agent_role="security",
            tenant_id=startup_spec.startup_id,
            capabilities=[
                "security_scanning",
                "compliance_validation",
                "vulnerability_assessment",
                "policy_enforcement"
            ],
            context={
                "compliance_frameworks": startup_spec.compliance_frameworks,
                "security_requirements": founder_analysis.get("security_needs", {})
            }
        )
        security_agent = await self.agent_spawner.spawn_agent(security_request)
        team_agents["security"] = security_agent
        self.agent_registry[security_agent.agent_id] = security_agent
        
        # Spawn Finance Agent  
        finance_request = AgentSpawnRequest(
            agent_role="finance",
            tenant_id=startup_spec.startup_id,
            capabilities=[
                "cost_optimization",
                "budget_planning",
                "resource_tracking",
                "financial_reporting"
            ],
            context={
                "funding_stage": startup_spec.funding_stage,
                "initial_budget": founder_analysis.get("budget_allocation", {})
            }
        )
        finance_agent = await self.agent_spawner.spawn_agent(finance_request)
        team_agents["finance"] = finance_agent
        self.agent_registry[finance_agent.agent_id] = finance_agent
        
        # Execute initial team coordination
        await self._coordinate_team_agents(team_agents, startup_spec)
        
        return team_agents
    
    async def _execute_final_validation(self, startup_id: str) -> Dict[str, Any]:
        """Execute final validation of complete startup setup"""
        
        startup_data = self.active_startups[startup_id]
        
        validation_results = {
            "github_org_operational": False,
            "azure_project_operational": False, 
            "agents_active": False,
            "governance_compliant": False,
            "audit_trail_complete": False
        }
        
        try:
            # Validate GitHub organization
            github_status = await self.governance_client.validate_github_org(
                startup_data["github_org"]
            )
            validation_results["github_org_operational"] = github_status["operational"]
            
            # Validate Azure DevOps project
            azure_status = await self.governance_client.validate_azure_project(
                startup_data["azure_project"]
            )
            validation_results["azure_project_operational"] = azure_status["operational"]
            
            # Validate agent status
            active_agents = [
                agent for agent in self.agent_registry.values()
                if agent.tenant_id == startup_id and agent.status == "active"
            ]
            validation_results["agents_active"] = len(active_agents) >= 4  # Bootstrap, Founder, Dev, Ops, Security, Finance
            
            # Validate governance compliance
            compliance_status = await self.governance_client.validate_compliance(startup_id)
            validation_results["governance_compliant"] = compliance_status["compliant"]
            
            # Validate audit trail
            audit_trail = await self.audit_manager.get_startup_audit_trail(startup_id)
            validation_results["audit_trail_complete"] = len(audit_trail) > 0
            
            # Overall validation
            all_valid = all(validation_results.values())
            
            logger.info("Final validation completed",
                       startup_id=startup_id,
                       validation_results=validation_results,
                       overall_valid=all_valid)
            
            return {
                "validation_results": validation_results,
                "overall_valid": all_valid,
                "validation_timestamp": datetime.utcnow()
            }
            
        except Exception as e:
            logger.error("Final validation failed", startup_id=startup_id, error=str(e))
            raise e
    
    async def _execute_agent_workflow(
        self, 
        agent_id: str, 
        workflow_type: str, 
        context: Any
    ) -> Dict[str, Any]:
        """Execute specific agent workflow"""
        
        # This would integrate with the specific agent implementation
        # For now, return mock results for development
        logger.info("Executing agent workflow", 
                   agent_id=agent_id, 
                   workflow_type=workflow_type)
        
        # Simulate workflow execution
        await asyncio.sleep(2)  # Simulate work
        
        return {
            "agent_id": agent_id,
            "workflow_type": workflow_type,
            "status": "completed",
            "results": {"mock": "data"},
            "execution_time": datetime.utcnow()
        }
    
    async def _coordinate_team_agents(
        self, 
        team_agents: Dict[str, AgentStatus], 
        startup_spec: StartupSpec
    ):
        """Coordinate team agents for initial setup"""
        
        # Coordinate parallel agent operations
        coordination_tasks = []
        
        for agent_role, agent in team_agents.items():
            task = self._execute_agent_workflow(
                agent.agent_id,
                f"{agent_role}_initialization_workflow",
                startup_spec
            )
            coordination_tasks.append(task)
        
        # Execute all agent workflows in parallel
        results = await asyncio.gather(*coordination_tasks, return_exceptions=True)
        
        logger.info("Team agent coordination completed",
                   startup_id=startup_spec.startup_id,
                   results=len(results))
    
    async def get_startup_status(self, startup_id: str) -> Dict[str, Any]:
        """Get current status of startup creation"""
        
        if startup_id not in self.active_startups:
            raise ValueError(f"Startup {startup_id} not found")
        
        startup_data = self.active_startups[startup_id]
        
        # Get agent statuses
        startup_agents = [
            agent for agent in self.agent_registry.values()
            if agent.tenant_id == startup_id
        ]
        
        return {
            "startup_id": startup_id,
            "status": startup_data["status"],
            "phases": startup_data["phases"],
            "github_org": startup_data.get("github_org"),
            "azure_project": startup_data.get("azure_project"),
            "agents": [
                {
                    "agent_id": agent.agent_id,
                    "role": agent.agent_role,
                    "status": agent.status,
                    "created_at": agent.created_at
                }
                for agent in startup_agents
            ],
            "created_at": startup_data["created_at"],
            "completed_at": startup_data.get("completed_at"),
            "error": startup_data.get("error")
        }
    
    async def get_metrics(self) -> Dict[str, Any]:
        """Get controller service metrics"""
        
        active_startups_count = len([
            s for s in self.active_startups.values()
            if s["status"] in ["orchestrating", "operational"]
        ])
        
        active_agents_count = len([
            a for a in self.agent_registry.values()
            if a.status == "active"
        ])
        
        return {
            "active_startups": active_startups_count,
            "total_startups": len(self.active_startups),
            "active_agents": active_agents_count,
            "total_agents": len(self.agent_registry),
            "service_uptime": "operational",
            "last_updated": datetime.utcnow()
        }
    
    async def cleanup(self):
        """Cleanup resources on shutdown"""
        logger.info("Cleaning up Controller Engine")
        
        # Revoke all active agent tokens
        for agent in self.agent_registry.values():
            if agent.status == "active":
                await self.agent_spawner.revoke_agent(agent.agent_id)
        
        await self.governance_client.cleanup()
        logger.info("Controller Engine cleanup completed")
