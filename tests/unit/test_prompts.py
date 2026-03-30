from unittest.mock import AsyncMock, MagicMock

import pytest

from velocity.prompts.library import PromptLibrary
from velocity.prompts.models import PromptVersion
from velocity.prompts.renderer import PromptCompilationError, render_prompt


@pytest.fixture
def mock_storage():
    storage = MagicMock()
    storage.fetch = AsyncMock()
    return storage

def test_render_prompt_basic():
    template = "Hello, {name}!"
    assert render_prompt(template, {"name": "Alice"}) == "Hello, Alice!"

def test_render_prompt_missing_var():
    template = "Hello, {name}! You are {age}."
    with pytest.raises(PromptCompilationError) as exc:
        render_prompt(template, {"name": "Alice"})
    assert "Missing required variable: 'age'" in str(exc.value)

@pytest.mark.asyncio
async def test_prompt_library_resolve_no_vars(mock_storage):
    library = PromptLibrary(storage_backend=mock_storage)
    
    mock_storage.fetch.return_value = PromptVersion(
        prompt_id="test", version="1.0", content="Base content"
    )
    
    content = await library.resolve("test@1.0")
    assert content == "Base content"
    assert mock_storage.fetch.call_count == 1
    
    # Second call should hit L1 cache
    content_cached = await library.resolve("test@1.0")
    assert content_cached == "Base content"
    assert mock_storage.fetch.call_count == 1

@pytest.mark.asyncio
async def test_prompt_library_resolve_with_vars(mock_storage):
    library = PromptLibrary(storage_backend=mock_storage)
    
    mock_storage.fetch.return_value = PromptVersion(
        prompt_id="greet", version="latest", content="Hello, {user}!"
    )
    
    content = await library.resolve("greet", {"user": "Bob"})
    assert content == "Hello, Bob!"
