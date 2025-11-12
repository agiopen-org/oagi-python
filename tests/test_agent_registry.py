import pytest

from oagi.agent import (
    AsyncAgent,
    async_agent_register,
    create_agent,
    get_agent_factory,
    list_agent_modes,
)
from oagi.agent.registry import _agent_registry
from oagi.types import AsyncActionHandler, AsyncImageProvider


class MockAsyncAgent:
    def __init__(self, **kwargs):
        self.kwargs = kwargs

    async def execute(
        self,
        instruction: str,
        action_handler: AsyncActionHandler,
        image_provider: AsyncImageProvider,
    ) -> bool:
        return True


class NotAnAgent:
    def __init__(self, **kwargs):
        pass


class SyncAgent:
    def __init__(self, **kwargs):
        pass

    def execute(
        self,
        instruction: str,
        action_handler: AsyncActionHandler,
        image_provider: AsyncImageProvider,
    ) -> bool:
        return True


class TestAgentRegistry:
    @pytest.fixture(autouse=True)
    def clear_test_registrations(self):
        # Store original registry
        original_registry = _agent_registry.copy()

        # Remove test modes if they exist
        test_modes = ["test_mode", "duplicate_mode", "invalid_mode"]
        for mode in test_modes:
            _agent_registry.pop(mode, None)

        yield

        # Restore original registry
        _agent_registry.clear()
        _agent_registry.update(original_registry)

    def test_register_and_retrieve_agent(self):
        @async_agent_register(mode="test_mode")
        def create_test_agent(
            api_key: str | None = None,
            base_url: str | None = None,
            model: str = "lux-v1",
        ) -> AsyncAgent:
            return MockAsyncAgent(api_key=api_key, base_url=base_url, model=model)

        # Retrieve factory
        factory = get_agent_factory("test_mode")
        assert factory is create_test_agent

        # Create agent using factory
        agent = factory(api_key="test-key", base_url="test-url", model="test-model")
        assert isinstance(agent, MockAsyncAgent)
        assert agent.kwargs["api_key"] == "test-key"
        assert agent.kwargs["base_url"] == "test-url"
        assert agent.kwargs["model"] == "test-model"

    def test_duplicate_registration_raises_error(self):
        @async_agent_register(mode="duplicate_mode")
        def create_agent1() -> AsyncAgent:
            return MockAsyncAgent()

        # Attempt to register the same mode again
        with pytest.raises(ValueError, match="already registered"):

            @async_agent_register(mode="duplicate_mode")
            def create_agent2() -> AsyncAgent:
                return MockAsyncAgent()

    def test_get_nonexistent_mode_raises_error(self):
        with pytest.raises(ValueError, match="Unknown agent mode"):
            get_agent_factory("nonexistent_mode")

    def test_list_agent_modes(self):
        # Get current modes (should include 'actor' and 'tasker' from factories)
        modes_before = set(list_agent_modes())

        # Register a test mode
        @async_agent_register(mode="test_mode")
        def create_test_agent() -> AsyncAgent:
            return MockAsyncAgent()

        # Check that the test mode is now listed
        modes_after = set(list_agent_modes())
        assert "test_mode" in modes_after
        assert modes_after - modes_before == {"test_mode"}

    def test_create_agent_with_parameter_filtering(self):
        @async_agent_register(mode="test_mode")
        def create_selective_agent(api_key: str, model: str) -> AsyncAgent:
            # This factory only accepts api_key and model
            return MockAsyncAgent(api_key=api_key, model=model)

        # Call create_agent with more parameters than the factory accepts
        agent = create_agent(
            mode="test_mode",
            api_key="test-key",
            base_url="test-url",  # Should be filtered out
            model="test-model",
            max_steps=30,  # Should be filtered out
            temperature=0.5,  # Should be filtered out
        )

        # Check that only the accepted parameters were passed
        assert isinstance(agent, MockAsyncAgent)
        assert agent.kwargs["api_key"] == "test-key"
        assert agent.kwargs["model"] == "test-model"
        assert "base_url" not in agent.kwargs
        assert "max_steps" not in agent.kwargs
        assert "temperature" not in agent.kwargs

    def test_create_agent_runtime_validation_no_execute(self):
        @async_agent_register(mode="invalid_mode")
        def create_invalid_agent() -> AsyncAgent:
            return NotAnAgent()

        with pytest.raises(TypeError, match="doesn't implement AsyncAgent protocol"):
            create_agent(mode="invalid_mode")

    def test_create_agent_runtime_validation_sync_execute(self):
        @async_agent_register(mode="invalid_mode")
        def create_sync_agent() -> AsyncAgent:
            return SyncAgent()

        with pytest.raises(TypeError, match="non-async 'execute' method"):
            create_agent(mode="invalid_mode")

    def test_built_in_modes_registered(self):
        modes = list_agent_modes()
        assert "actor" in modes
        assert "tasker" in modes or "tasker:cat" in modes

    def test_create_built_in_actor_agent(self):
        agent = create_agent(
            mode="actor",
            api_key="test-key",
            base_url="test-url",
            model="lux-v1",
            max_steps=20,
            temperature=0.5,
        )
        # Should create AsyncDefaultAgent
        assert hasattr(agent, "execute")
        assert hasattr(agent, "api_key")
        assert agent.api_key == "test-key"
        assert agent.model == "lux-v1"
        assert agent.max_steps == 20

    def test_create_built_in_tasker_agent(self):
        agent = create_agent(
            mode="tasker",
            api_key="test-key",
            base_url="test-url",
            model="lux-v1",
            max_steps=25,
            temperature=0.2,
            reflection_interval=15,
        )
        # Should create TaskerAgent
        assert hasattr(agent, "execute")
        assert hasattr(agent, "api_key")
        assert agent.api_key == "test-key"
        assert agent.model == "lux-v1"
        assert agent.max_steps == 25
        assert agent.reflection_interval == 15

    def test_factory_with_no_parameters(self):
        @async_agent_register(mode="test_mode")
        def create_no_param_agent() -> AsyncAgent:
            return MockAsyncAgent(fixed="value")

        agent = create_agent(
            mode="test_mode",
            api_key="test-key",
            model="test-model",
        )
        assert isinstance(agent, MockAsyncAgent)
        assert agent.kwargs["fixed"] == "value"
        assert "api_key" not in agent.kwargs
        assert "model" not in agent.kwargs

    def test_factory_with_kwargs(self):
        @async_agent_register(mode="test_mode")
        def create_kwargs_agent(**kwargs) -> AsyncAgent:
            return MockAsyncAgent(**kwargs)

        agent = create_agent(
            mode="test_mode",
            api_key="test-key",
            base_url="test-url",
            model="test-model",
            custom_param="custom-value",
        )
        assert isinstance(agent, MockAsyncAgent)
        assert agent.kwargs["api_key"] == "test-key"
        assert agent.kwargs["base_url"] == "test-url"
        assert agent.kwargs["model"] == "test-model"
        assert agent.kwargs["custom_param"] == "custom-value"
