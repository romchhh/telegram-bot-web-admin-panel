def format_entities(text, entities):
    if not entities:
        return text
    
    formatted_text = text
    shift = 0
    
    tag_map = {
        'bold': ('<b>', '</b>'),
        'italic': ('<i>', '</i>'),
        'underline': ('<u>', '</u>'),
        'strikethrough': ('<s>', '</s>'),
        'spoiler': ('<tg-spoiler>', '</tg-spoiler>'),
        'pre': ('<pre>', '</pre>'),
        'monospace': ('<code>', '</code>'),
        'blockquote': ('<blockquote>', '</blockquote>'),
    }
    
    for entity in sorted(entities, key=lambda e: e.offset):
        entity_type = entity.type
        offset = entity.offset
        length = entity.length
        
        emoji_count_start = count_emoji_before(text, offset)
        emoji_count_end = count_emoji_before(text, offset + length)
        
        adjusted_offset = offset + shift - emoji_count_start
        adjusted_length = length - (emoji_count_end - emoji_count_start)
        
        entity_text = formatted_text[adjusted_offset:adjusted_offset + adjusted_length]
        
        if entity_type == 'custom_emoji':
            continue
        
        if entity_type in tag_map:
            start_tag, end_tag = tag_map[entity_type]
        elif entity_type == 'text_link':
            start_tag = f'<a href="{entity.url}">'
            end_tag = '</a>'
        else:
            continue
        
        formatted_text = (
            formatted_text[:adjusted_offset] +
            f"{start_tag}{entity_text}{end_tag}" +
            formatted_text[adjusted_offset + adjusted_length:]
        )
        
        shift += len(start_tag) + len(end_tag)
    
    return formatted_text


def count_emoji_before(text, position):
        emoji_count = 0
        for i, char in enumerate(text):
            if i >= position:
                break
            if 0x1F000 <= ord(char) <= 0x1FFFF:
                emoji_count += 1
        return emoji_count


def parse_url_buttons(text):
    buttons = []
    lines = text.split('\n')
    for line in lines:
        if ' | ' in line:
            parts = line.split(' | ')
            row = []
            for part in parts:
                button_parts = part.split(' - ')
                if len(button_parts) == 2:
                    button_text = button_parts[0].strip()
                    button_url = button_parts[1].strip()
                    row.append((button_text, button_url))
            buttons.append(row)
        else:
            button_parts = line.split(' - ')
            if len(button_parts) == 2:
                button_text = button_parts[0].strip()
                button_url = button_parts[1].strip()
                buttons.append([(button_text, button_url)])
    return buttons





