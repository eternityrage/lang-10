import os
import sys
import time
import json
import pathlib
import subprocess
import requests

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

def get_page_credentials(brand_name):
    # Check direct environment variables first
    brand_upper = brand_name.upper()
    page_token = os.getenv(f'{brand_upper}_PAGE_TOKEN') or os.getenv('FACEBOOK_ACCESS_TOKEN')
    page_id = os.getenv(f'{brand_upper}_PAGE_ID') or os.getenv('FACEBOOK_PAGE_ID')

    if page_token and page_id:
        return page_id, page_token

    # Check local page_tokens.json fallback (same directory as publisher.py)
    token_file = pathlib.Path(__file__).parent / 'page_tokens.json'
    if token_file.exists():
        with open(token_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            if brand_upper in data:
                return data[brand_upper]['PAGE_ID'], data[brand_upper]['PAGE_TOKEN']

    return None, None

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
