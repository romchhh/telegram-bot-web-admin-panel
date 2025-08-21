import json
import os
from typing import Dict, Any
from database.settings_db import get_setting, update_setting, get_start_message_config, get_all_settings


def load_settings():
    settings = get_all_settings()
    
    json_fields = ['start_inline_buttons']
    for field in json_fields:
        if field in settings and settings[field]:
            try:
                if isinstance(settings[field], str):
                    parsed_value = json.loads(settings[field])
                else:
                    parsed_value = settings[field]
                
                if isinstance(parsed_value, list):
                    settings[field] = parsed_value
                else:
                    settings[field] = []
            except (json.JSONDecodeError, TypeError):
                settings[field] = []
        else:
            settings[field] = []
    
    return settings

def save_settings(settings):
    for key, value in settings.items():
        update_setting(key, value)
