import asyncio
import httpx
from typing import Optional, Dict, Any


class AIProviderClient:
    """
    Python SDK for AI Provider Agent Service
    
    Provides easy integration for other agent services to use the
    centralized AI provider routing capabilities.
    """
    
    def __init__(self, base_url: str = "http://localhost:8080", api_key: Optional[str] = None):
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.client = httpx.AsyncClient()
        
    async def __aenter__(self):
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()
    
    def _get_headers(self) -> Dict[str, str]:
        """Get headers for requests"""
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers
    
    async def health_check(self) -> Dict[str, Any]:
        """Check service health"""
        response = await self.client.get(
            f"{self.base_url}/health",
            headers=self._get_headers()
        )
        response.raise_for_status()
        return response.json()
    
    async def process(
        self,
        task_type: str,
        prompt: str,
        model: str = "auto",
        max_tokens: int = 1000,
        temperature: float = 0.7,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Process an AI request
        
        Args:
            task_type: Type of task (thinking, coding, writing, etc.)
            prompt: The prompt to process
            model: Specific model to use or 'auto' for intelligent routing
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            **kwargs: Additional parameters
            
        Returns:
            AI response with content, provider info, and usage stats
        """
        request_data = {
            "task_type": task_type,
            "prompt": prompt,
            "model": model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            **kwargs
        }
        
        response = await self.client.post(
            f"{self.base_url}/ai/process",
            json=request_data,
            headers=self._get_headers()
        )
        response.raise_for_status()
        return response.json()
    
    async def get_provider_status(self) -> Dict[str, Any]:
        """Get status of all providers"""
        response = await self.client.get(
            f"{self.base_url}/providers/status",
            headers=self._get_headers()
        )
        response.raise_for_status()
        return response.json()
    
    async def get_metrics(self) -> str:
        """Get Prometheus metrics"""
        response = await self.client.get(
            f"{self.base_url}/metrics",
            headers=self._get_headers()
        )
        response.raise_for_status()
        return response.text


# Convenience functions for common tasks
class TaskTemplates:
    """Pre-defined task templates for common use cases"""
    
    @staticmethod
    async def generate_code(
        client: AIProviderClient,
        requirements: str,
        language: str = "python",
        max_tokens: int = 2000
    ) -> Dict[str, Any]:
        """Generate code based on requirements"""
        prompt = f"Generate {language} code for the following requirements:\n\n{requirements}\n\nProvide clean, well-documented code with error handling."
        return await client.process(
            task_type="coding",
            prompt=prompt,
            max_tokens=max_tokens
        )
    
    @staticmethod
    async def review_code(
        client: AIProviderClient,
        code: str,
        focus_areas: str = "bugs, performance, security"
    ) -> Dict[str, Any]:
        """Review code for issues"""
        prompt = f"Review the following code focusing on: {focus_areas}\n\n```\n{code}\n```\n\nProvide specific feedback and suggestions for improvement."
        return await client.process(
            task_type="review",
            prompt=prompt
        )
    
    @staticmethod
    async def analyze_data(
        client: AIProviderClient,
        data_description: str,
        analysis_goals: str
    ) -> Dict[str, Any]:
        """Analyze data and provide insights"""
        prompt = f"Analyze the following data: {data_description}\n\nGoals: {analysis_goals}\n\nProvide insights, patterns, and recommendations."
        return await client.process(
            task_type="analysis",
            prompt=prompt
        )
    
    @staticmethod
    async def write_documentation(
        client: AIProviderClient,
        code_or_feature: str,
        doc_type: str = "user guide"
    ) -> Dict[str, Any]:
        """Generate documentation"""
        prompt = f"Write a {doc_type} for the following:\n\n{code_or_feature}\n\nMake it clear, comprehensive, and user-friendly."
        return await client.process(
            task_type="writing",
            prompt=prompt
        )


# Example usage for agent services
class ExampleDevAgent:
    """Example integration for a Development Agent"""
    
    def __init__(self, ai_provider_url: str = "http://localhost:8080"):
        self.ai_client = AIProviderClient(ai_provider_url)
    
    async def implement_feature(self, feature_description: str, language: str = "python"):
        """Implement a feature using AI assistance"""
        try:
            # Generate initial code
            code_response = await TaskTemplates.generate_code(
                self.ai_client,
                feature_description,
                language
            )
            
            generated_code = code_response["content"]
            
            # Review the generated code
            review_response = await TaskTemplates.review_code(
                self.ai_client,
                generated_code
            )
            
            return {
                "code": generated_code,
                "review": review_response["content"],
                "provider_used": code_response["provider"],
                "total_tokens": code_response["tokens_used"] + review_response["tokens_used"]
            }
            
        except httpx.HTTPStatusError as e:
            return {"error": f"AI Provider service error: {e}"}
        except Exception as e:
            return {"error": f"Unexpected error: {e}"}


class ExampleQAAgent:
    """Example integration for a QA Agent"""
    
    def __init__(self, ai_provider_url: str = "http://localhost:8080"):
        self.ai_client = AIProviderClient(ai_provider_url)
    
    async def generate_test_cases(self, feature_description: str):
        """Generate test cases for a feature"""
        prompt = f"""
        Generate comprehensive test cases for the following feature:
        
        {feature_description}
        
        Include:
        - Unit tests
        - Integration tests
        - Edge cases
        - Error conditions
        
        Use pytest format and include both positive and negative test scenarios.
        """
        
        try:
            response = await self.ai_client.process(
                task_type="coding",
                prompt=prompt,
                max_tokens=2000
            )
            
            return {
                "test_cases": response["content"],
                "provider": response["provider"],
                "tokens_used": response["tokens_used"]
            }
            
        except Exception as e:
            return {"error": str(e)}


# Async context manager for easy usage
async def main_example():
    """Example of using the AI Provider Client"""
    
    async with AIProviderClient() as client:
        # Check service health
        health = await client.health_check()
        print(f"Service status: {health}")
        
        # Generate code
        response = await client.process(
            task_type="coding",
            prompt="Write a Python function to calculate fibonacci numbers",
            max_tokens=500
        )
        
        print(f"Generated code:\n{response['content']}")
        print(f"Used provider: {response['provider']}")
        print(f"Tokens used: {response['tokens_used']}")


if __name__ == "__main__":
    asyncio.run(main_example())
