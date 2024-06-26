# Copyright (c) Microsoft. All rights reserved.
# Licensed under the MIT license. See LICENSE.md file in the project root for full license information.

import pytest
import json
import os

from azure.ai.assistant.management.assistant_client import AssistantClient
from azure.ai.assistant.management.assistant_config import AssistantConfig, VectorStoreConfig
from azure.ai.assistant.management.ai_client_factory import AIClientType
from azure.ai.assistant.management.conversation_thread_client import ConversationThreadClient

import time
from pathlib import Path


RESOURCES_PATH = Path(__file__).parent / 'resources'
MODEL_ENV_VAR = os.environ.get('OPENAI_ASSISTANT_MODEL', 'gpt-4-1106-preview')

def generate_test_config(updates=None):
    """
    Generates a base test configuration with no selected functions by default, sets the model from an environment variable, and applies updates from the `updates` dictionary.

    :param updates: A dictionary containing updates to the base configuration.
    :return: A configuration dictionary with the updates applied.
    """
    base_config = {
        "name": "assistant_test",
        "instructions": "You are test assistant with awareness of time",
        "model": MODEL_ENV_VAR,  # Use the model from the environment variable
        "tool_resources": {},
        "functions": [],
        "file_search": False,
        "code_interpreter": False,
        "output_folder_path": "output",
        "ai_client_type": "OPEN_AI"
    }

    if updates:
        def update(d, u):
            for k, v in u.items():
                if isinstance(v, dict):
                    d[k] = update(d.get(k, {}), v)
                else:
                    d[k] = v
            return d

        update(base_config, updates)

    return base_config

def test_assistant_client_init():
    config = generate_test_config()
    config_json = json.dumps(config)

    client = AssistantClient(config_json)
    assert client.name == "assistant_test"
    assert client._ai_client_type == AIClientType.OPEN_AI
    assert client._ai_client is not None
    assert client._callbacks is not None
    assert client._functions == {}
    client.purge()

def test_assistant_client_from_json():
    config = generate_test_config()
    config_json = json.dumps(config)

    client = AssistantClient.from_json(config_json)
    assert client.name == "assistant_test"
    assert client._ai_client_type == AIClientType.OPEN_AI
    assert client._ai_client is not None
    assert client._callbacks is not None
    assert client._functions == {}
    client.purge()

def test_assistant_client_sync_from_cloud():
    config = generate_test_config()
    config_json = json.dumps(config)

    client = AssistantClient.from_json(config_json)
    client = client.sync_from_cloud()
    assert client.name == "assistant_test"
    assert client._ai_client_type == AIClientType.OPEN_AI
    assert client._ai_client is not None
    assert client._callbacks is not None
    assert client._functions == {}
    client.purge()

def test_assistant_client_update():
    config = generate_test_config()
    config_json = json.dumps(config)

    client = AssistantClient.from_json(config_json)
    client.assistant_config.instructions = "these are updated instructions"
    config_json = client.assistant_config.to_json()

    client.from_json(config_json)
    assert client.assistant_config.instructions == "these are updated instructions"
    client.purge()

def test_assistant_client_purge():
    config = generate_test_config()
    config_json = json.dumps(config)

    client = AssistantClient.from_json(config_json)
    client.purge()

def test_assistant_client_add_fetch_current_datetime_function():
    # Adding the fetch_current_datetime function in the update
    updates = {
        "functions": [
            {
                "type": "function",
                "function": {
                    "name": "fetch_current_datetime",
                    "module": "azure.ai.assistant.functions.file_functions",
                    "description": "Get the current time as a JSON string.",
                    "parameters": {
                        "type": "object",
                        "properties": {},
                        "required": []
                    }
                }
            },
        ]
    }

    config = generate_test_config(updates)
    config_json = json.dumps(config)
    client = AssistantClient.from_json(config_json)
    client = client.sync_from_cloud()
    assert len(client.assistant_config.functions) == 1
    assert client.assistant_config.functions[0]['function']['name'] == "fetch_current_datetime"
    client.purge()

def skip_test_assistant_client_enable_file_search():
    updates = {
        "file_search": True
    }

    config = generate_test_config(updates)
    config_json = json.dumps(config)
    client = AssistantClient.from_json(config_json)
    client = client.sync_from_cloud()
    assert client.assistant_config.file_search == True
    client.purge()

def test_assistant_client_tool_resources_file_search_create_with_file_json():
    file1 = str(RESOURCES_PATH / "product_info_1.md")
    tool_resources = {
        "code_interpreter": {
            "files": {}
        },
        "file_search": {
            "vector_stores": [
                {
                    "name": "test_vector_store",
                    "id": None,
                    "files": {
                        file1: None
                    },
                    "metadata": {},
                    "expires_after": None
                }
            ]
        }
    }
    updates = {
        "tool_resources": tool_resources,
        "file_search": True
    }

    config = generate_test_config(updates)
    config_json = json.dumps(config)
    client = AssistantClient.from_json(config_json)
    assert client.assistant_config.file_search == True
    vs_id = client.assistant_config.tool_resources.file_search_vector_stores[0].id
    assert vs_id is not None
    file_id = client.assistant_config.tool_resources.file_search_vector_stores[0].files[file1]
    assert file_id is not None
    client.ai_client.beta.vector_stores.delete(vector_store_id=vs_id)
    client.ai_client.files.delete(file_id)
    client.purge()

def test_assistant_client_tool_resources_file_search_create_with_file_config():
    config_data = generate_test_config()
    assistant_config = AssistantConfig(config_data)
    file_1 = str(RESOURCES_PATH / "product_info_1.md")
    assistant_config.file_search = True
    assistant_config.tool_resources.code_interpreter_files = {}
    vs_config = VectorStoreConfig(name="test_vector_store",
                                  id=None,
                                  files={file_1: None},
                                  metadata={},
                                  expires_after=None)
    assistant_config.tool_resources.file_search_vector_stores = [vs_config]
    client = AssistantClient.from_config(assistant_config)
    assert client.assistant_config.file_search == True
    vs_id = client.assistant_config.tool_resources.file_search_vector_stores[0].id
    assert vs_id is not None
    file_id = client.assistant_config.tool_resources.file_search_vector_stores[0].files[file_1]
    assert file_id is not None
    client.ai_client.beta.vector_stores.delete(vector_store_id=vs_id)
    client.ai_client.files.delete(file_id)
    client.purge()

def test_assistant_client_enable_code_interpreter():
    updates = {
        "code_interpreter": True
    }

    config = generate_test_config(updates)
    config_json = json.dumps(config)
    client = AssistantClient.from_json(config_json)
    client = client.sync_from_cloud()
    assert client.assistant_config.code_interpreter == True
    client.purge()

def test_assistant_client_create_thread_and_process_message():
    config = generate_test_config()
    config_json = json.dumps(config)

    client = AssistantClient.from_json(config_json)
    thread_client = ConversationThreadClient.get_instance(AIClientType.OPEN_AI)
    thread_name = thread_client.create_conversation_thread()
    thread_client.create_conversation_thread_message("Hello!", thread_name)
    client.process_messages(thread_name)
    conversation = thread_client.retrieve_conversation(thread_name)
    last_message = conversation.get_last_text_message(client.assistant_config.name)
    assert last_message is not None
    client.purge()