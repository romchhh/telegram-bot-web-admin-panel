from aiogram import Bot
from aiogram.types import URLInputFile, Message
from aiogram.enums import ChatAction
from main import bot

video_cache = {}

def get_video_cache():
    return video_cache

def set_video_cache(key: str, file_id: str):
    video_cache[key] = file_id

def get_cached_video(key: str):
    return video_cache.get(key)

def is_video_cached(key: str):
    return key in video_cache

def clear_video_cache():
    global video_cache
    video_cache.clear()

def get_cache_stats():
    return {
        'total_cached': len(video_cache),
        'keys': list(video_cache.keys())
    }


async def send_video_with_caching_for_mailing(bot: Bot, user_id: int, video_url: str, caption: str, reply_markup=None, cache_key: str = "mailing_video"):
    try:
        if not video_url.startswith(('http://', 'https://')):
            await bot.send_video(
                chat_id=user_id,
                video=video_url,
                caption=caption,
                parse_mode="HTML",
                reply_markup=reply_markup
            )
            return True
        
        if is_video_cached(cache_key):
            file_id = get_cached_video(cache_key)
            
            try:
                await bot.send_video(
                    chat_id=user_id,
                    video=file_id,
                    caption=caption,
                    parse_mode="HTML",
                    reply_markup=reply_markup
                )
                return True
            except Exception as e:
                print(f"Failed to send cached video: {e}, will try to re-upload")
        
        await bot.send_chat_action(chat_id=user_id, action="upload_video")
        
        try:
            from aiogram.types import URLInputFile
            video = URLInputFile(video_url, filename="video.mp4")
            
            sent_message = await bot.send_video(
                chat_id=user_id,
                video=video,
                caption=caption,
                parse_mode="HTML",
                reply_markup=reply_markup,
                width=1280,
                    height=720,
                supports_streaming=True
            )
            
            if sent_message and sent_message.video:
                set_video_cache(cache_key, sent_message.video.file_id)
                return True
                
        except Exception as e:
            
            try:
                video = URLInputFile(video_url, filename="video.mp4")
                sent_message = await bot.send_video(
                    chat_id=user_id,
                    video=video,
                    caption=caption,
                    parse_mode="HTML",
                    reply_markup=reply_markup,
                    supports_streaming=True
                )
                
                if sent_message and sent_message.video:
                    set_video_cache(cache_key, sent_message.video.file_id)
                    return True
                    
            except Exception as e2:
                return False
            
    except Exception as e:
        return False
    


async def send_video_with_caching(message: Message, video_url: str, caption: str, reply_markup=None, cache_key: str = "default_video"):
    try:
        if not video_url.startswith(('http://', 'https://')):
            await message.answer_video(
                video=video_url,
                caption=caption,
                parse_mode="HTML",
                reply_markup=reply_markup
            )
            return True
            
        if is_video_cached(cache_key):
            await message.answer_video(
                video=get_cached_video(cache_key),
                caption=caption,
                parse_mode="HTML",
                reply_markup=reply_markup
            )
            return True
        else:
            await bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.UPLOAD_VIDEO)
            video = URLInputFile(video_url, filename="video.mp4")
            
            try:
                sent_message = await message.answer_video(
                    video,
                    caption=caption,
                    parse_mode="HTML",
                    reply_markup=reply_markup,
                    width=1280,
                    height=720,
                    supports_streaming=True
                )
                
                if sent_message.video:
                    set_video_cache(cache_key, sent_message.video.file_id)
                    return True
                    
            except Exception as e:
                
                video = URLInputFile(video_url, filename="video.mp4")
                sent_message = await message.answer_video(
                    video,
                    caption=caption,
                    parse_mode="HTML",
                    reply_markup=reply_markup,
                    supports_streaming=True
                )
                
                if sent_message.video:
                    set_video_cache(cache_key, sent_message.video.file_id)
                    return True
            
    except Exception as e:
        try:
            video = URLInputFile(video_url, filename="video.mp4")
            await message.answer_document(
                video, 
                caption=caption + " (як документ)",
                parse_mode="HTML",
                reply_markup=reply_markup
            )
            return True
        except Exception as e2:
            return False
    
    return False