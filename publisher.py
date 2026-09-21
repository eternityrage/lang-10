import os
import sys
import time
import json
import pathlib
import subprocess
import requests

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

from datetime import datetime, timezone
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

ISO_MAP = {
    'JA': 'KOTOKA', 'HE': 'IVRINA', 'ES': 'VOBLO', 'FR': 'DIMOI', 'DE': 'SPRACHO',
    'IT': 'DICOO', 'KO': 'MALAMOO', 'ZH': 'BOHUA', 'RU': 'GOVORO', 'PT': 'FALOO'
}

def get_page_credentials(code):
    code_upper = code.upper()
    lookup_key = ISO_MAP.get(code_upper, code_upper)

    # Check environment variables (either ISO code or legacy secret name)
    page_token = (os.getenv(f'{code_upper}_PAGE_TOKEN') or 
                  os.getenv(f'{lookup_key}_PAGE_TOKEN') or 
                  os.getenv('FACEBOOK_ACCESS_TOKEN'))
    page_id = (os.getenv(f'{code_upper}_PAGE_ID') or 
               os.getenv(f'{lookup_key}_PAGE_ID') or 
               os.getenv('FACEBOOK_PAGE_ID'))

    if page_token and page_id:
        return page_id, page_token

    # Check local page_tokens.json fallback
    token_file = pathlib.Path(__file__).parent / 'page_tokens.json'
    if token_file.exists():
        with open(token_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            if lookup_key in data:
                return data[lookup_key]['PAGE_ID'], data[lookup_key]['PAGE_TOKEN']
            if code_upper in data:
                return data[code_upper]['PAGE_ID'], data[code_upper]['PAGE_TOKEN']

    return None, None

def get_youtube_credentials(code):
    code_upper = code.upper()
    lookup_key = ISO_MAP.get(code_upper, code_upper)

    client_id = (os.getenv('YOUTUBE_CLIENT_ID') or os.getenv('YT_CLIENT_ID', '')).strip()
    client_secret = (os.getenv('YOUTUBE_CLIENT_SECRET') or os.getenv('YT_CLIENT_SECRET', '')).strip()
    refresh_token = (os.getenv(f'{code_upper}_YT_REFRESH_TOKEN') or
                     os.getenv(f'{lookup_key}_YT_REFRESH_TOKEN') or
                     os.getenv('YOUTUBE_REFRESH_TOKEN', '')).strip()

    if client_id and client_secret and refresh_token:
        return client_id, client_secret, refresh_token

    # Fallback to local youtube_tokens.json
    yt_file = pathlib.Path(__file__).parent / 'youtube_tokens.json'
    if yt_file.exists():
        try:
            with open(yt_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            entry = data.get(code_upper) or data.get(lookup_key)
            if entry:
                cid = entry.get('client_id') or client_id
                csec = entry.get('client_secret') or client_secret
                rt = entry.get('refresh_token')
                if cid and csec and rt:
                    return cid, csec, rt
        except Exception as e:
            print(f"[{code}] Note loading youtube_tokens.json: {e}")

    return None, None, None

def should_upload_to_youtube(lang_code, mode='auto', min_interval_hours=9.0):
    """
    Ensures YouTube only publishes TWICE a day (spaced by at least min_interval_hours),
    while Facebook can publish 4 times a day.
    """
    mode = (mode or 'auto').lower()
    if mode == 'skip':
        return False, "YouTube upload explicitly disabled (mode=skip)"
    if mode == 'force':
        return True, "YouTube upload forced (mode=force)"

    # Check environment variable overrides
    if os.getenv('SKIP_YOUTUBE', '').lower() in ('true', '1', 'yes'):
        return False, "Skipped by SKIP_YOUTUBE env"
    if os.getenv('FORCE_YOUTUBE', '').lower() in ('true', '1', 'yes'):
        return True, "Forced by FORCE_YOUTUBE env"

    hist_file = pathlib.Path(__file__).parent / lang_code / 'output' / 'history' / 'youtube_history.json'
    if not hist_file.exists():
        return True, "Initial YouTube upload for this channel"

    try:
        with open(hist_file, 'r', encoding='utf-8') as f:
            hist_data = json.load(f)
        uploads = hist_data.get('uploads', [])
        if not uploads:
            return True, "No prior YouTube uploads in history"

        now = datetime.now(timezone.utc)
        
        # Parse last upload time
        last_entry = uploads[-1]
        last_str = last_entry.get('timestamp')
        last_dt = datetime.fromisoformat(last_str)
        if last_dt.tzinfo is None:
            last_dt = last_dt.replace(tzinfo=timezone.utc)

        elapsed_hours = (now - last_dt).total_seconds() / 3600.0

        # Count uploads in last 24 hours
        recent_24h = []
        for u in uploads:
            u_dt = datetime.fromisoformat(u['timestamp'])
            if u_dt.tzinfo is None:
                u_dt = u_dt.replace(tzinfo=timezone.utc)
            if (now - u_dt).total_seconds() < 86400:
                recent_24h.append(u)

        if len(recent_24h) >= 2:
            return False, f"Daily 2-video quota reached ({len(recent_24h)} uploads in last 24h, last {elapsed_hours:.1f}h ago)"

        if elapsed_hours < min_interval_hours:
            return False, f"Cooldown active: {elapsed_hours:.1f}h elapsed since last upload (min interval is {min_interval_hours}h)"

        return True, f"Eligible for YouTube upload ({len(recent_24h)} in last 24h, last {elapsed_hours:.1f}h ago)"
    except Exception as e:
        print(f"[{lang_code}] Warning checking YouTube history: {e}")
        return True, "History check fallback"

def record_youtube_upload(lang_code, video_id, topic):
    hist_dir = pathlib.Path(__file__).parent / lang_code / 'output' / 'history'
    hist_dir.mkdir(parents=True, exist_ok=True)
    hist_file = hist_dir / 'youtube_history.json'
    data = {'uploads': []}
    if hist_file.exists():
        try:
            with open(hist_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except Exception:
            pass

    data.setdefault('uploads', []).append({
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'video_id': video_id,
        'topic': topic,
        'url': f'https://youtube.com/shorts/{video_id}'
    })

    with open(hist_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def post_youtube_comment(youtube, video_id, description, brand_name):
    print(f"[{brand_name}] Adding YouTube study notes comment...")
    time.sleep(3)
    comment_text = (
        f"📝 MINI LESSON STUDY NOTES:\n\n"
        f"{description}\n\n"
        f"💡 Challenge: Repeat each line out loud 3 times! Which phrase did you like the most? Drop your answer in the comments! 👇"
    )
    try:
        req = youtube.commentThreads().insert(
            part="snippet",
            body={
                "snippet": {
                    "videoId": video_id,
                    "topLevelComment": {
                        "snippet": {
                            "textOriginal": comment_text
                        }
                    }
                }
            }
        )
        res = req.execute()
        cid = res.get('id')
        print(f"[{brand_name}] YouTube study comment posted! (ID: {cid})")
        return cid
    except Exception as e:
        print(f"[{brand_name}] Note on YouTube comment: {e}")
        return None

def upload_reel_to_youtube(video_path, title, description, tags, brand_name):
    print(f"\n============================================================")
    print(f"[{brand_name.upper()}] PUBLISHING TO YOUTUBE SHORTS (2x DAILY SCHEDULE)")
    print(f"============================================================")

    client_id, client_secret, refresh_token = get_youtube_credentials(brand_name)
    if not client_id or not client_secret or not refresh_token:
        print(f"[{brand_name}] ⚠️ Missing YouTube credentials for {brand_name}. Skipping YouTube upload.")
        return {'status': 'skipped', 'error': 'Missing YouTube credentials'}

    video_path_obj = pathlib.Path(video_path)
    if not video_path_obj.exists():
        print(f"[{brand_name}] ❌ Video file not found: {video_path}")
        return {'status': 'failed', 'error': 'Video file not found'}

    try:
        creds = Credentials(
            None,
            refresh_token=refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=client_id,
            client_secret=client_secret,
            scopes=["https://www.googleapis.com/auth/youtube"]
        )
        creds.refresh(Request())
        youtube = build('youtube', 'v3', credentials=creds)

        # Ensure title fits YouTube 100 character limit
        clean_title = title.strip()
        if len(clean_title) > 90:
            clean_title = clean_title[:87] + "..."
        if "#Shorts" not in clean_title and len(clean_title) + 8 <= 100:
            clean_title = f"{clean_title} #Shorts"

        yt_desc = description.strip()
        if "#Shorts" not in yt_desc:
            yt_desc = f"{yt_desc}\n\n#Shorts #LanguageLearning"

        body = {
            'snippet': {
                'title': clean_title,
                'description': yt_desc,
                'tags': tags or ['language learning', 'shorts', 'education'],
                'categoryId': '27'  # Education
            },
            'status': {
                'privacyStatus': 'public',
                'selfDeclaredMadeForKids': False,
            }
        }

        media = MediaFileUpload(
            str(video_path_obj),
            chunksize=-1,
            resumable=True,
            mimetype='video/mp4'
        )

        print(f"[{brand_name}] Uploading YouTube Short: {clean_title}")
        req = youtube.videos().insert(
            part=','.join(body.keys()),
            body=body,
            media_body=media
        )

        response = None
        while response is None:
            status, response = req.next_chunk()
            if status:
                print(f"[{brand_name}] YouTube Upload Progress: {int(status.progress() * 100)}%")

        video_id = response.get('id')
        yt_url = f"https://youtube.com/shorts/{video_id}"
        print(f"[{brand_name}] [OK] YOUTUBE SHORT PUBLISHED: {yt_url}")

        # Post study comment
        post_youtube_comment(youtube, video_id, description, brand_name)

        # Record upload in history
        record_youtube_upload(brand_name, video_id, clean_title)

        return {'status': 'success', 'video_id': video_id, 'url': yt_url, 'platform': 'youtube'}

    except Exception as e:
        print(f"[{brand_name}] [ERR] YouTube Upload Error: {e}")
        return {'status': 'failed', 'error': str(e)}

def upload_reel_to_facebook(video_path, title, description, brand_name):
    print(f"\n============================================================")
    print(f"[{brand_name.upper()}] PUBLISHING TO FACEBOOK REELS")
    print(f"============================================================")

    page_id, access_token = get_page_credentials(brand_name)
    if not page_id or not access_token:
        print(f"[{brand_name}] ⚠️ Missing Page ID or Access Token. Skipping upload.")
        return {'status': 'skipped', 'error': 'Missing credentials'}

    video_path_obj = pathlib.Path(video_path)
    if not video_path_obj.exists():
        print(f"[{brand_name}] ❌ Video file not found: {video_path}")
        return {'status': 'failed', 'error': 'Video file not found'}

    file_size = video_path_obj.stat().st_size
    api_base = "https://graph.facebook.com/v21.0"

    try:
        # Step 1: Initialize Reel upload
        start_url = f"{api_base}/{page_id}/video_reels"
        start_data = {'access_token': access_token, 'upload_phase': 'start', 'file_size': file_size}
        res_start = requests.post(start_url, data=start_data, timeout=30)
        if res_start.status_code != 200:
            raise Exception(f"Reel init failed: {res_start.text}")

        s_json = res_start.json()
        video_id = s_json.get('video_id')
        upload_url = s_json.get('upload_url')
        if not video_id or not upload_url:
            raise Exception(f"Invalid init response: {s_json}")

        print(f"[{brand_name}] Step 1 OK: Video ID {video_id}")

        # Step 2: Transfer video bytes
        print(f"[{brand_name}] Step 2: Transferring video binary ({file_size / (1024*1024):.2f} MB)...")
        headers = {'Authorization': f'OAuth {access_token}', 'offset': '0', 'file_size': str(file_size)}
        with open(video_path_obj, 'rb') as f:
            res_up = requests.post(upload_url, headers=headers, data=f, timeout=300)
        if res_up.status_code != 200:
            raise Exception(f"Video binary upload failed: {res_up.text}")

        # Step 3: Finish and Publish
        print(f"[{brand_name}] Step 3: Finalizing publication...")
        finish_data = {
            'access_token': access_token,
            'upload_phase': 'finish',
            'video_id': video_id,
            'title': title,
            'description': description,
            'video_state': 'PUBLISHED'
        }
        res_finish = requests.post(start_url, data=finish_data, timeout=60)
        if res_finish.status_code == 200 and res_finish.json().get('success'):
            print(f"[{brand_name}] [OK] FACEBOOK REEL PUBLISHED: https://facebook.com/{video_id}")
            fb_res = {'status': 'success', 'video_id': video_id, 'platform': 'facebook'}
            
            # Post viral pinned comment with dialogue notes
            post_pinned_comment(video_id, description, access_token, brand_name)
        else:
            raise Exception(f"Publish finalization failed: {res_finish.text}")

        # Auto-detect connected Instagram Account and publish if available
        upload_to_connected_instagram(video_path_obj, description, page_id, access_token, brand_name)
        return fb_res

    except Exception as e:
        print(f"[{brand_name}] [ERR] Facebook Upload Error: {e}")
        return {'status': 'failed', 'error': str(e)}

def post_pinned_comment(video_id, description, access_token, brand_name):
    print(f"[{brand_name}] Adding pinned conversation study comment...")
    time.sleep(5)
    
    pinned_text = (
        f"📝 MINI LESSON STUDY NOTES:\n\n"
        f"{description}\n\n"
        f"💡 Challenge: Repeat each line out loud 3 times! Which phrase did you like the most? Drop your answer in the comments below! 👇"
    )
    
    comment_url = f"https://graph.facebook.com/v21.0/{video_id}/comments"
    for attempt in range(5):
        try:
            res = requests.post(comment_url, data={'access_token': access_token, 'message': pinned_text}, timeout=20)
            if res.status_code == 200:
                cid = res.json().get('id')
                print(f"[{brand_name}] Study comment posted! (ID: {cid})")
                # Try pinning comment
                requests.post(f"https://graph.facebook.com/v21.0/{cid}", data={'access_token': access_token, 'is_pinned': 'true'}, timeout=15)
                break
            elif res.status_code in (400, 404):
                time.sleep(8)
        except Exception as e:
            print(f"[{brand_name}] Pinned comment note: {e}")
            break

def upload_to_connected_instagram(video_path_obj, caption, page_id, access_token, brand_name):
    print(f"[{brand_name}] Checking for connected Instagram Business Account...")
    try:
        ig_r = requests.get(
            f"https://graph.facebook.com/v21.0/{page_id}",
            params={'fields': 'instagram_business_account', 'access_token': access_token},
            timeout=15
        )
        if ig_r.status_code != 200:
            print(f"[{brand_name}] IG check skipped: {ig_r.text[:80]}")
            return

        ig_acct = ig_r.json().get('instagram_business_account')
        if not ig_acct or not ig_acct.get('id'):
            print(f"[{brand_name}] ℹ️ No Instagram account linked to this Facebook Page yet. Skipping IG.")
            return

        ig_user_id = ig_acct['id']
        print(f"[{brand_name}] 📸 Found connected Instagram Account ID: {ig_user_id}")

        file_size = video_path_obj.stat().st_size
        api_base = "https://graph.facebook.com/v21.0"

        c_params = {
            'media_type': 'REELS',
            'upload_type': 'resumable',
            'caption': caption[:2200],
            'access_token': access_token,
            'share_to_feed': False
        }
        c_res = requests.post(f"{api_base}/{ig_user_id}/media", params=c_params, timeout=30)
        if c_res.status_code not in (200, 201):
            print(f"[{brand_name}] IG container failed: {c_res.text}")
            return

        c_data = c_res.json()
        container_id = c_data.get('id')
        upload_uri = c_data.get('uri')

        with open(video_path_obj, 'rb') as f:
            v_bytes = f.read()

        up_headers = {
            'Authorization': f'OAuth {access_token}',
            'offset': '0',
            'file_size': str(file_size),
            'Content-Type': 'video/mp4'
        }
        requests.post(upload_uri, headers=up_headers, data=v_bytes, timeout=120)

        # Wait for Meta transcoding
        time.sleep(35)
        pub_res = requests.post(
            f"{api_base}/{ig_user_id}/media_publish",
            params={'creation_id': container_id, 'access_token': access_token},
            timeout=60
        )
        if pub_res.status_code in (200, 201):
            ig_media_id = pub_res.json().get('id', container_id)
            print(f"[{brand_name}] ✅ INSTAGRAM REEL PUBLISHED! Media ID: {ig_media_id}")
    except Exception as ig_err:
        print(f"[{brand_name}] ⚠️ Instagram upload notice: {ig_err}")
