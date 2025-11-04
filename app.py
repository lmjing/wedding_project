from flask import Flask, render_template_string, send_from_directory, request, jsonify, redirect, url_for, flash, abort, session
import os
import json
import shutil
import time
import re
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta

app = Flask(__name__)
app.secret_key = 'wedding_admin_secret_key_2025'

ADMIN_PASSWORD = '1215'

# 업로드 설정
UPLOAD_FOLDER = 'assets/images'
GALLERY_FOLDER = 'assets/images/gallery'
VIDEO_FOLDER = 'assets/videos'
AUDIO_FOLDER = 'assets/audio'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'svg', 'webp', 'mp4', 'mov', 'avi', 'webm', 'mp3', 'wav', 'ogg', 'm4a', 'aac'}
VIDEO_EXTENSIONS = {'mp4', 'mov', 'avi', 'webm'}
AUDIO_EXTENSIONS = {'mp3', 'wav', 'ogg', 'm4a', 'aac'}

INVITATIONS_DIR = 'invitations'
INVITATIONS_INDEX_FILE = os.path.join(INVITATIONS_DIR, 'index.json')
DEFAULT_INVITATION_SLUG = 'default'
RESERVED_SLUGS = {'admin', 'assets', 'static', 'api', 'guestbook', 'favicon.ico', 'robots.txt'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100MB 제한 (영상 때문에 증가)


def ensure_invitations_root():
    os.makedirs(INVITATIONS_DIR, exist_ok=True)


def invitations_index_template():
    return {
        'default_slug': None,
        'invitations': []
    }


def load_invitations_index():
    ensure_invitations_root()
    if not os.path.exists(INVITATIONS_INDEX_FILE):
        return invitations_index_template()
    try:
        with open(INVITATIONS_INDEX_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            if 'default_slug' not in data:
                data['default_slug'] = None
            if 'invitations' not in data:
                data['invitations'] = []
            return data
    except (json.JSONDecodeError, FileNotFoundError):
        return invitations_index_template()


def save_invitations_index(index_data):
    ensure_invitations_root()
    with open(INVITATIONS_INDEX_FILE, 'w', encoding='utf-8') as f:
        json.dump(index_data, f, ensure_ascii=False, indent=4)


def slugify_name(name):
    base = secure_filename(name or '').lower()
    base = base.replace('_', '-')
    base = re.sub(r'[^a-z0-9\-]+', '', base)
    base = re.sub(r'-{2,}', '-', base).strip('-')
    if not base:
        base = f'invitation-{int(time.time())}'
    return base


def ensure_invitation_directory(slug):
    ensure_invitations_root()
    base_path = os.path.join(INVITATIONS_DIR, slug)
    assets_base = os.path.join(base_path, 'assets')
    images_path = os.path.join(assets_base, 'images')
    gallery_path = os.path.join(images_path, 'gallery')
    videos_path = os.path.join(assets_base, 'videos')
    audio_path = os.path.join(assets_base, 'audio')

    os.makedirs(base_path, exist_ok=True)
    os.makedirs(gallery_path, exist_ok=True)
    os.makedirs(videos_path, exist_ok=True)
    os.makedirs(audio_path, exist_ok=True)

    return {
        'base': base_path,
        'assets': assets_base,
        'images': images_path,
        'gallery': gallery_path,
        'videos': videos_path,
        'audio': audio_path,
    }


def get_custom_template_path(slug):
    if not slug:
        return None
    return os.path.join(INVITATIONS_DIR, slug, 'template.html')


def get_invitation_config_path(slug):
    return os.path.join(INVITATIONS_DIR, slug, 'config.json')


def list_invitations():
    index = load_invitations_index()
    invitations = []
    for entry in index.get('invitations', []):
        if entry.get('slug'):
            invitations.append(entry)
    # 누락된 디렉토리를 정리
    unique = {}
    for entry in invitations:
        unique[entry['slug']] = entry
    sorted_entries = sorted(unique.values(), key=lambda item: item.get('created_at', ''))
    return sorted_entries


def get_default_invitation_slug():
    index = load_invitations_index()
    default_slug = index.get('default_slug')
    if default_slug:
        return default_slug
    entries = list_invitations()
    if entries:
        return entries[0]['slug']
    return None


def invitation_exists(slug):
    config_path = get_invitation_config_path(slug)
    return os.path.exists(config_path)


def resolve_invitation_slug(default_to_current=True):
    slug = request.args.get('slug') if request.args else None
    if not slug and request.form:
        slug = request.form.get('invitation_slug') or request.form.get('slug')
    if not slug and request.is_json:
        try:
            data = request.get_json(silent=True) or {}
            slug = data.get('slug') or data.get('invitation_slug')
        except Exception:
            slug = None

    if slug in RESERVED_SLUGS:
        return None

    if slug:
        return slug

    if default_to_current:
        return get_default_invitation_slug()

    return None


def to_invitation_file_path(slug, relative_path):
    if not relative_path:
        return None

    if str(relative_path).startswith(('http://', 'https://', '//')):
        return None

    normalized = str(relative_path).lstrip('/')
    return os.path.join(INVITATIONS_DIR, slug, normalized)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def is_video_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in VIDEO_EXTENSIONS

def is_audio_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in AUDIO_EXTENSIONS

def load_config(invitation_slug=None):
    """설정 파일 로드"""
    if invitation_slug:
        config_path = get_invitation_config_path(invitation_slug)
    else:
        config_path = 'config.json'

    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        # 기본 설정 반환
        return {}


def save_config(config, invitation_slug=None):
    """설정 파일 저장"""
    if invitation_slug:
        ensure_invitation_directory(invitation_slug)
        config_path = get_invitation_config_path(invitation_slug)
    else:
        config_path = 'config.json'

    with open(config_path, 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=4)


def default_invitation_config(name=None, slug=None):
    display_name = name or '새로운 청첩장'
    now_iso = datetime.utcnow().isoformat()
    return {
        'meta': {
            'name': display_name,
            'slug': slug,
            'created_at': now_iso,
            'updated_at': now_iso,
            'thumbnail': '',
        },
        'wedding_info': {
            'groom_name': '신랑',
            'bride_name': '신부',
            'wedding_date': '2026-01-18',
            'wedding_time': '오전 11시 30분',
            'wedding_venue': '예식장',
            'wedding_address': '주소',
        },
        'family_info': {
            'groom_father': '아버지',
            'groom_mother': '어머니',
            'bride_father': '아버지',
            'bride_mother': '어머니',
        },
        'messages': {
            'invitation_message': '',
            'poem_message': '',
            'outro_message': '',
        },
        'transportation': {
            'subway': '',
            'bus': '',
            'parking': '',
        },
        'account_info': {
            'groom_accounts': [],
            'bride_accounts': [],
        },
        'images': {
            'main_photo': 'assets/images/main-photo.jpg',
            'invitation_photo': 'assets/images/invitation-photo.jpg',
            'photobooth_photo': 'assets/images/photobooth.jpg',
            'outro_photo': 'assets/images/outro-photo.jpg',
            'invitation_photo_type': 'image',
            'outro_photo_type': 'image',
        },
        'gallery_images': [],
        'api_keys': {
            'naver_map_client_id': '',
        },
        'audio': {
            'background_music': '',
            'autoplay': False,
            'loop': False,
            'volume': 50,
        },
        'map': {
            'image': '',
            'link': '',
        },
    }


def ensure_unique_slug(slug):
    ensure_invitations_root()
    existing = {entry['slug'] for entry in list_invitations()}
    if slug not in existing:
        return slug

    suffix = 2
    while True:
        candidate = f"{slug}-{suffix}"
        if candidate not in existing:
            return candidate
        suffix += 1


def copy_invitation_assets(from_slug, to_slug):
    source_dir = os.path.join(INVITATIONS_DIR, from_slug, 'assets')
    target_dir = os.path.join(INVITATIONS_DIR, to_slug, 'assets')

    if not os.path.exists(source_dir):
        return

    for root_dir, _, files in os.walk(source_dir):
        relative_root = os.path.relpath(root_dir, source_dir)
        destination_root = os.path.join(target_dir, relative_root) if relative_root != '.' else target_dir
        os.makedirs(destination_root, exist_ok=True)
        for file_name in files:
            shutil.copy2(os.path.join(root_dir, file_name), os.path.join(destination_root, file_name))


def create_invitation(name, slug=None, source_config=None, make_default=False, copy_from_slug=None):
    ensure_invitations_root()
    raw_slug = slug or slugify_name(name)
    if raw_slug in RESERVED_SLUGS:
        raw_slug = f"{raw_slug}-inv"
    slug = ensure_unique_slug(raw_slug)

    directories = ensure_invitation_directory(slug)

    if copy_from_slug and invitation_exists(copy_from_slug):
        copy_invitation_assets(copy_from_slug, slug)

    config = source_config or default_invitation_config(name, slug)
    if 'meta' not in config:
        config['meta'] = {}
    config['meta'].update({
        'name': name,
        'slug': slug,
        'updated_at': datetime.utcnow().isoformat(),
    })
    config['meta'].setdefault('created_at', datetime.utcnow().isoformat())
    config['meta'].setdefault('thumbnail', '')

    save_config(config, invitation_slug=slug)

    index = load_invitations_index()
    existing_slugs = {item['slug'] for item in index.get('invitations', [])}
    if slug not in existing_slugs:
        index.setdefault('invitations', []).append({
            'slug': slug,
            'name': name,
            'created_at': config['meta'].get('created_at'),
            'updated_at': config['meta'].get('updated_at'),
            'thumbnail': config['meta'].get('thumbnail', ''),
        })

    if make_default or not index.get('default_slug'):
        index['default_slug'] = slug

    save_invitations_index(index)

    return {
        'slug': slug,
        'directories': directories,
        'config': config,
    }


def rename_invitation_slug(old_slug, desired_slug):
    if not invitation_exists(old_slug):
        raise ValueError('청첩장을 찾을 수 없습니다.')

    desired_slug = (desired_slug or '').strip()
    if not desired_slug:
        raise ValueError('새 슬러그를 입력해주세요.')

    new_slug = slugify_name(desired_slug)
    if not new_slug:
        raise ValueError('유효한 슬러그를 입력해주세요.')

    if new_slug in RESERVED_SLUGS:
        raise ValueError('사용할 수 없는 슬러그입니다.')

    if new_slug == old_slug:
        return new_slug

    if invitation_exists(new_slug):
        raise ValueError('이미 사용 중인 슬러그입니다.')

    old_path = os.path.join(INVITATIONS_DIR, old_slug)
    new_path = os.path.join(INVITATIONS_DIR, new_slug)

    if not os.path.exists(old_path):
        raise ValueError('기존 청첩장 디렉토리를 찾을 수 없습니다.')

    os.makedirs(os.path.dirname(new_path), exist_ok=True)
    shutil.move(old_path, new_path)

    index = load_invitations_index()
    for entry in index.get('invitations', []):
        if entry.get('slug') == old_slug:
            entry['slug'] = new_slug
            entry['updated_at'] = datetime.utcnow().isoformat()
            break

    if index.get('default_slug') == old_slug:
        index['default_slug'] = new_slug

    save_invitations_index(index)

    config = load_config(new_slug)
    config.setdefault('meta', {})
    config['meta']['slug'] = new_slug
    config['meta']['updated_at'] = datetime.utcnow().isoformat()
    save_config(config, invitation_slug=new_slug)

    sync_invitation_index(new_slug, config)

    return new_slug


def ensure_default_invitation():
    index = load_invitations_index()
    if index.get('invitations'):
        return index

    legacy_config_path = 'config.json'
    if os.path.exists(legacy_config_path):
        try:
            with open(legacy_config_path, 'r', encoding='utf-8') as f:
                legacy_config = json.load(f)
        except json.JSONDecodeError:
            legacy_config = {}
    else:
        legacy_config = {}

    name_from_config = legacy_config.get('meta', {}).get('name')
    if not name_from_config:
        groom = legacy_config.get('wedding_info', {}).get('groom_name', '신랑')
        bride = legacy_config.get('wedding_info', {}).get('bride_name', '신부')
        name_from_config = f"{groom} ♥ {bride}"

    created = create_invitation(name_from_config, slug=DEFAULT_INVITATION_SLUG, source_config=legacy_config, make_default=True)

    # 기존 에셋을 기본 청첩장 폴더로 복사 (이미 존재하면 건너뜀)
    source_assets = {
        'images': UPLOAD_FOLDER,
        'gallery': GALLERY_FOLDER,
        'videos': VIDEO_FOLDER,
        'audio': AUDIO_FOLDER,
    }

    for key, src in source_assets.items():
        if not os.path.exists(src):
            continue
        dst = created['directories'][key if key != 'gallery' else 'images']
        if key == 'gallery':
            dst = created['directories']['gallery']
        try:
            for root_dir, _, files in os.walk(src):
                relative_root = os.path.relpath(root_dir, src)
                target_root = os.path.join(dst, relative_root) if relative_root != '.' else dst
                os.makedirs(target_root, exist_ok=True)
                for file_name in files:
                    src_file = os.path.join(root_dir, file_name)
                    dst_file = os.path.join(target_root, file_name)
                    if not os.path.exists(dst_file):
                        shutil.copy2(src_file, dst_file)
        except Exception:
            # 에셋 복사 실패는 치명적이지 않으므로 무시
            pass

    return load_invitations_index()


def set_default_invitation(slug):
    index = load_invitations_index()
    slugs = {entry['slug'] for entry in index.get('invitations', [])}
    if slug not in slugs:
        raise ValueError('해당 청첩장을 찾을 수 없습니다.')

    index['default_slug'] = slug
    save_invitations_index(index)
    return index


def delete_invitation(slug):
    if not invitation_exists(slug):
        raise ValueError('삭제할 청첩장을 찾을 수 없습니다.')

    index = load_invitations_index()
    invitations = [entry for entry in index.get('invitations', []) if entry.get('slug') != slug]

    if not invitations:
        raise ValueError('최소 한 개의 청첩장은 유지해야 합니다.')

    invitation_path = os.path.join(INVITATIONS_DIR, slug)
    if os.path.exists(invitation_path):
        shutil.rmtree(invitation_path, ignore_errors=True)

    index['invitations'] = invitations
    if index.get('default_slug') == slug:
        index['default_slug'] = invitations[0]['slug']

    save_invitations_index(index)
    return index


def sync_invitation_index(slug, config=None):
    index = load_invitations_index()
    meta_config = config or load_config(slug)
    meta = meta_config.get('meta', {})

    entry_found = False
    for entry in index.get('invitations', []):
        if entry.get('slug') == slug:
            entry['name'] = meta.get('name', entry.get('name'))
            entry['updated_at'] = meta.get('updated_at', entry.get('updated_at'))
            thumbnail_path = meta.get('thumbnail', '')
            if thumbnail_path:
                entry['thumbnail'] = thumbnail_path
            elif 'thumbnail' in entry:
                entry.pop('thumbnail')
            entry_found = True
            break

    if not entry_found:
        entry = {
            'slug': slug,
            'name': meta.get('name', slug),
            'created_at': meta.get('created_at', datetime.utcnow().isoformat()),
            'updated_at': meta.get('updated_at', datetime.utcnow().isoformat()),
        }
        thumbnail_path = meta.get('thumbnail', '')
        if thumbnail_path:
            entry['thumbnail'] = thumbnail_path
        index.setdefault('invitations', []).append(entry)

    save_invitations_index(index)


def update_invitation_meta(slug, name=None):
    if not invitation_exists(slug):
        raise ValueError('청첩장을 찾을 수 없습니다.')

    config = load_config(slug)
    config.setdefault('meta', {})

    if name:
        config['meta']['name'] = name

    config['meta']['updated_at'] = datetime.utcnow().isoformat()
    save_config(config, invitation_slug=slug)

    sync_invitation_index(slug, config)

    return config


def get_guestbook_path(slug):
    if not invitation_exists(slug):
        raise ValueError('청첩장을 찾을 수 없습니다.')
    ensure_invitation_directory(slug)
    return os.path.join(INVITATIONS_DIR, slug, 'guestbook.json')


def load_guestbook_entries(slug):
    if not slug or not invitation_exists(slug):
        return []

    path = get_guestbook_path(slug)
    if not os.path.exists(path):
        legacy_path = 'guestbook.json'
        default_slug = get_default_invitation_slug()
        if slug == default_slug and os.path.exists(legacy_path):
            with open(legacy_path, 'r', encoding='utf-8') as f:
                try:
                    entries = json.load(f)
                except json.JSONDecodeError:
                    entries = []
            save_guestbook_entries(slug, entries)
            return entries
        return []

    with open(path, 'r', encoding='utf-8') as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return []


def save_guestbook_entries(slug, entries):
    if not slug or not invitation_exists(slug):
        raise ValueError('청첩장을 찾을 수 없습니다.')

    path = get_guestbook_path(slug)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(entries, f, ensure_ascii=False, indent=2)


def get_rsvp_path(slug):
    if not slug or not invitation_exists(slug):
        raise ValueError('청첩장을 찾을 수 없습니다.')
    ensure_invitation_directory(slug)
    return os.path.join(INVITATIONS_DIR, slug, 'rsvp.json')


def load_rsvp_entries(slug):
    if not slug or not invitation_exists(slug):
        return []

    path = get_rsvp_path(slug)
    if not os.path.exists(path):
        return []

    with open(path, 'r', encoding='utf-8') as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return []


def save_rsvp_entries(slug, entries):
    if not slug or not invitation_exists(slug):
        raise ValueError('청첩장을 찾을 수 없습니다.')

    path = get_rsvp_path(slug)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(entries, f, ensure_ascii=False, indent=2)


def get_visit_log_path(slug):
    if not slug or not invitation_exists(slug):
        raise ValueError('청첩장을 찾을 수 없습니다.')
    ensure_invitation_directory(slug)
    return os.path.join(INVITATIONS_DIR, slug, 'visits.json')


def load_visit_entries(slug):
    if not slug or not invitation_exists(slug):
        return []

    path = get_visit_log_path(slug)
    if not os.path.exists(path):
        return []

    with open(path, 'r', encoding='utf-8') as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return []


def save_visit_entries(slug, entries):
    if not slug or not invitation_exists(slug):
        raise ValueError('청첩장을 찾을 수 없습니다.')

    path = get_visit_log_path(slug)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(entries, f, ensure_ascii=False, indent=2)


def record_visit(slug):
    try:
        ip_candidates = request.headers.get('X-Forwarded-For', request.remote_addr or '').split(',')
        ip_address = (ip_candidates[0] or '').strip() or 'unknown'
        user_agent = request.headers.get('User-Agent', 'Unknown')
        path = request.path
        timestamp = datetime.utcnow().isoformat()

        entries = load_visit_entries(slug)
        entry_map = {entry.get('ip'): entry for entry in entries if entry.get('ip')}

        entry = entry_map.get(ip_address)
        if not entry:
            entry = {
                'ip': ip_address,
                'visits': [],
                'user_agents': [],
                'count': 0,
            }
            entries.append(entry)
            entry_map[ip_address] = entry

        entry['count'] = entry.get('count', 0) + 1
        visits = entry.get('visits', [])
        visits.append({'timestamp': timestamp, 'path': path})
        # Limit stored visits per IP to last 50 entries
        entry['visits'] = visits[-50:]
        entry['last_seen'] = timestamp
        entry['last_path'] = path

        user_agents = entry.get('user_agents', [])
        if user_agent and user_agent not in user_agents:
            user_agents.insert(0, user_agent)
            entry['user_agents'] = user_agents[:10]

        # Sort entries by last_seen descending
        entries.sort(key=lambda item: item.get('last_seen', ''), reverse=True)
        save_visit_entries(slug, entries)
    except Exception as exc:
        app.logger.warning(f'방문 로그 저장 실패: {exc}')


def is_admin_authenticated():
    return session.get('admin_authenticated') is True


@app.before_request
def require_admin_authentication():
    if request.path.startswith('/admin'):
        if request.endpoint in {'admin_login', 'admin_logout'}:
            return
        if request.path.startswith(('/admin/assets', '/admin/css', '/admin/js')):
            return
        if not is_admin_authenticated():
            next_url = request.url if request.method == 'GET' else url_for('admin')
            return redirect(url_for('admin_login', next=next_url))


@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        password = (request.form.get('password') or '').strip()
        if password == ADMIN_PASSWORD:
            session['admin_authenticated'] = True
            flash('로그인되었습니다.', 'success')
            next_url = request.form.get('next') or request.args.get('next') or url_for('admin')
            return redirect(next_url)
        else:
            flash('비밀번호가 올바르지 않습니다.', 'error')

    if is_admin_authenticated():
        next_url = request.args.get('next') or url_for('admin')
        return redirect(next_url)

    return render_template_string(ADMIN_LOGIN_TEMPLATE, next_url=request.args.get('next', ''))


@app.route('/admin/logout')
def admin_logout():
    session.pop('admin_authenticated', None)
    flash('로그아웃되었습니다.', 'success')
    return redirect(url_for('admin_login'))

def generate_invitation_html(config, slug=None):
    """지정된 청첩장 설정을 기반으로 index.html 생성"""
    config = config or {}

    template_path = 'index_template.html'
    if slug:
        custom_template = get_custom_template_path(slug)
        if custom_template and os.path.exists(custom_template):
            template_path = custom_template

    with open(template_path, 'r', encoding='utf-8') as f:
        template = f.read()

    wedding_info = config.get('wedding_info', {})
    family_info = config.get('family_info', {})
    messages = config.get('messages', {})
    transportation = config.get('transportation', {})
    images = config.get('images', {})

    def asset_url(path_value):
        if not path_value:
            return ''
        path_value = str(path_value)
        if path_value.startswith(('http://', 'https://', '//')):
            return path_value
        if path_value.startswith('/'):
            return path_value
        normalized = path_value.lstrip('/')
        if slug:
            return f'/{slug}/{normalized}'
        return f'/{normalized}'

    def clean_text(value, fallback=''):
        if isinstance(value, str):
            value = value.strip()
        elif value is None:
            value = ''
        else:
            value = str(value).strip()
        return value or fallback

    groom_name_clean = clean_text(wedding_info.get('groom_name'), '신랑')
    bride_name_clean = clean_text(wedding_info.get('bride_name'), '신부')
    wedding_date_clean = clean_text(wedding_info.get('wedding_date'))
    wedding_time_clean = clean_text(wedding_info.get('wedding_time'))
    wedding_venue_clean = clean_text(wedding_info.get('wedding_venue'))
    wedding_address_clean = clean_text(wedding_info.get('wedding_address'))

    page_title = f"{groom_name_clean} ♥ {bride_name_clean} 결혼합니다"
    description_parts = [part for part in [wedding_date_clean, wedding_time_clean, wedding_venue_clean] if part]
    page_description = ' '.join(description_parts) or page_title

    meta_config = config.get('meta', {})
    og_image_source = meta_config.get('thumbnail') or images.get('main_photo') or 'assets/images/main-photo.jpg'

    replacements = {
        '{{groom_name}}': groom_name_clean,
        '{{bride_name}}': bride_name_clean,
        '{{wedding_date}}': wedding_date_clean or '2026-01-18',
        '{{wedding_time}}': wedding_time_clean or '오전 11시 30분',
        '{{wedding_venue}}': wedding_venue_clean or '예식장',
        '{{wedding_address}}': wedding_address_clean or '주소',
        '{{groom_father}}': family_info.get('groom_father', '아버지'),
        '{{groom_mother}}': family_info.get('groom_mother', '어머니'),
        '{{bride_father}}': family_info.get('bride_father', '아버지'),
        '{{bride_mother}}': family_info.get('bride_mother', '어머니'),
        '{{invitation_message}}': messages.get('invitation_message', ''),
        '{{poem_message}}': messages.get('poem_message', ''),
        '{{outro_message}}': messages.get('outro_message', ''),
        '{{subway_info}}': transportation.get('subway', ''),
        '{{bus_info}}': transportation.get('bus', ''),
        '{{parking_info}}': transportation.get('parking', ''),
        '{{main_photo}}': asset_url(images.get('main_photo', 'assets/images/main-photo.jpg')),
        '{{invitation_photo}}': asset_url(images.get('invitation_photo', 'assets/images/invitation-photo.jpg')),
        '{{photobooth_photo}}': asset_url(images.get('photobooth_photo', 'assets/images/photobooth.jpg')),
        '{{outro_photo}}': asset_url(images.get('outro_photo', 'assets/images/outro-photo.jpg')),
        '{{page_title}}': page_title,
        '{{page_description}}': page_description,
        '{{og_image}}': asset_url(og_image_source),
    }

    map_settings = config.get('map_settings', {})
    if map_settings.get('mapImage'):
        map_image_path = asset_url(map_settings['mapImage'])
        replacements['{{map_image}}'] = f'<img src="{map_image_path}" alt="지도" style="width: 100%; height: auto; border-radius: 6px;">'
    else:
        replacements['{{map_image}}'] = '<div style="width: 100%; height: 200px; background: #f0f0f0; border-radius: 6px; display: flex; align-items: center; justify-content: center; color: #999;">지도 이미지</div>'

    if map_settings:
        if map_settings.get('subwayInfo'):
            replacements['{{subway_info}}'] = map_settings['subwayInfo']
        if map_settings.get('busInfo'):
            replacements['{{bus_info}}'] = map_settings['busInfo']
        if map_settings.get('parkingInfo'):
            replacements['{{parking_info}}'] = map_settings['parkingInfo']

    account_info = config.get('account_info', {})
    groom_accounts_html = ""
    for account in account_info.get('groom_accounts', []):
        groom_accounts_html += f'''
        <div class="text gothic">
            <div class="inner">
                <span><span class="bank">{account['bank']}</span> <span>{account['number']}</span></span><br>
                <span>{account['name']}</span>
            </div>
            <div>
                <div class="btn-action" onclick="copyAccount('{account['bank']} {account['number']} {account['name']}')">
                    <svg viewBox="0.48 0.48 23.04 23.04" fill="#222F3D">
                        <path fill="none" d="M0 0h24v24H0z"></path>
                        <path d="M16 1H4c-1.1 0-2 .9-2 2v14h2V3h12V1zm3 4H8c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h11c1.1 0 2-.9 2-2V7c0-1.1-.9-2-2-2zm0 16H8V7h11v14z"></path>
                    </svg>
                    복사
                </div>
            </div>
        </div>'''

    bride_accounts_html = ""
    for account in account_info.get('bride_accounts', []):
        bride_accounts_html += f'''
        <div class="text gothic">
            <div class="inner">
                <span><span class="bank">{account['bank']}</span> <span>{account['number']}</span></span><br>
                <span>{account['name']}</span>
            </div>
            <div>
                <div class="btn-action" onclick="copyAccount('{account['bank']} {account['number']} {account['name']}')">
                    <svg viewBox="0.48 0.48 23.04 23.04" fill="#222F3D">
                        <path fill="none" d="M0 0h24v24H0z"></path>
                        <path d="M16 1H4c-1.1 0-2 .9-2 2v14h2V3h12V1zm3 4H8c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h11c1.1 0 2-.9 2-2V7c0-1.1-.9-2-2-2zm0 16H8V7h11v14z"></path>
                    </svg>
                    복사
                </div>
            </div>
        </div>'''

    replacements['{{groom_accounts}}'] = groom_accounts_html
    replacements['{{bride_accounts}}'] = bride_accounts_html

    map_html = ""
    if config.get('map') and config['map'].get('image'):
        map_image = asset_url(config['map']['image'])
        map_link = config['map'].get('link', '')

        if map_link:
            map_html = f'''
            <div class="map-image-container" style="text-align: center; margin: 20px 0;">
                <a href="{map_link}" target="_blank" rel="noopener noreferrer" style="display: inline-block; cursor: pointer;">
                    <img src="{map_image}" alt="오시는 길 지도" style="max-width: 100%; height: auto; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1);">
                </a>
                <p style="margin-top: 10px; font-size: 0.9rem; color: var(--subtitle-text-color);">지도를 클릭하면 상세한 길찾기를 확인할 수 있습니다</p>
            </div>'''
        else:
            map_html = f'''
            <div class="map-image-container" style="text-align: center; margin: 20px 0;">
                <img src="{map_image}" alt="오시는 길 지도" style="max-width: 100%; height: auto; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1);">
            </div>'''

    replacements['{{map_image}}'] = map_html or replacements['{{map_image}}']

    gallery_images = config.get('gallery_images', [])
    gallery_html = ""

    animation_classes = [
        'fade-in-up',
        'fade-in-up fade-in-delay-1',
        'fade-in-up fade-in-delay-2',
        'fade-in-up fade-in-delay-3',
        'fade-in-up fade-in-delay-1',
        'fade-in-up fade-in-delay-2',
        'fade-in-up fade-in-delay-3',
        'fade-in-up',
        'fade-in-up fade-in-delay-1'
    ]

    for i, image_data in enumerate(gallery_images):
        if isinstance(image_data, dict):
            image_path = image_data.get('path', '')
            size = image_data.get('size', 'small')
            media_type = image_data.get('type', 'image')
        else:
            image_path = image_data
            size = 'small'
            media_type = 'image'

        if size == 'tall':
            aspect_ratio = "16 / 20"
            column = (i % 2) + 1
            grid_area = f"span 2 / {column} / auto / {column + 1}"
        else:
            aspect_ratio = "16 / 10"
            column = (i % 2) + 1
            grid_area = f"span 1 / {column} / auto / {column + 1}"

        animation_class = animation_classes[i % len(animation_classes)]

        media_path = asset_url(image_path)

        if media_type == 'video':
            gallery_html += f'''
        <div class="grid-item {animation_class}" style="grid-area: {grid_area};">
            <div class="item video-item" style="aspect-ratio: {aspect_ratio};" data-video="{media_path}">
                <video class="gallery-video" muted loop playsinline preload="metadata">
                    <source src="{media_path}" type="video/mp4">
                </video>
            </div>
        </div>'''
        elif media_type == 'url_image':
            gallery_html += f'''
        <div class="grid-item {animation_class}" style="grid-area: {grid_area};">
            <div class="item" style="background-image: url('{media_path}'); aspect-ratio: {aspect_ratio};" onclick="openImageModal('{media_path}')" data-url-image="true"></div>
        </div>'''
        else:
            gallery_html += f'''
        <div class="grid-item {animation_class}" style="grid-area: {grid_area};">
            <div class="item" style="background-image: url('{media_path}'); aspect-ratio: {aspect_ratio};" onclick="openImageModal('{media_path}')"></div>
        </div>'''

    replacements['{{gallery_images}}'] = gallery_html

    background_audio_html = ''
    audio_config = config.get('audio', {})
    if audio_config.get('background_music'):
        audio_path = asset_url(audio_config.get('background_music'))
        volume = audio_config.get('volume', 50) / 100.0

        background_audio_html = f'''
    <script>
        // 배경음악 설정을 전역 변수로 설정
        window.backgroundMusicConfig = {{
            url: "{audio_path}",
            autoplay: {str(audio_config.get('autoplay', True)).lower()},
            loop: {str(audio_config.get('loop', True)).lower()},
            volume: {volume}
        }};
        console.log('🎵 배경음악 설정:', window.backgroundMusicConfig);
    </script>'''

    replacements['{{background_audio}}'] = background_audio_html

    invitation_media_html = ''
    if images.get('invitation_photo'):
        invitation_path = asset_url(images.get('invitation_photo'))
        invitation_type = images.get('invitation_photo_type', 'image')

        if invitation_type == 'video':
            invitation_media_html = f'''<video src="{invitation_path}" class="img-blur gallery-video" muted loop playsinline preload="metadata" style="width: 100%; height: auto;">
                <source src="{invitation_path}" type="video/mp4">
                영상을 지원하지 않는 브라우저입니다.
            </video>'''
        else:
            invitation_media_html = f'<img src="{invitation_path}" class="img-blur" alt="초대 사진">'
    else:
        invitation_media_html = f'<img src="{asset_url("assets/images/invitation-photo.jpg")}" class="img-blur" alt="초대 사진">'

    replacements['{{invitation_media}}'] = invitation_media_html

    outro_media_html = ''
    if images.get('outro_photo'):
        outro_path = asset_url(images.get('outro_photo'))
        outro_type = images.get('outro_photo_type', 'image')

        if outro_type == 'video':
            outro_media_html = f'''<video src="{outro_path}" class="img-blur darken gallery-video" muted loop playsinline preload="metadata" style="width: 100%; height: auto;">
                <source src="{outro_path}" type="video/mp4">
                영상을 지원하지 않는 브라우저입니다.
            </video>'''
        else:
            outro_media_html = f'<img src="{outro_path}" class="img-blur darken" alt="마무리 사진">'
    else:
        outro_media_html = f'<img src="{asset_url("assets/images/outro-photo.jpg")}" class="img-blur darken" alt="마무리 사진">'

    replacements['{{outro_media}}'] = outro_media_html

    html_content = template
    for key, value in replacements.items():
        html_content = html_content.replace(key, str(value))

    if slug:
        replacements_map = {
            'href="assets/': f'href="/{slug}/assets/',
            "href='assets/": f"href='/{slug}/assets/",
            'src="assets/': f'src="/{slug}/assets/',
            "src='assets/": f"src='/{slug}/assets/",
            'url("assets/': f'url("/{slug}/assets/',
            "url('assets/": f"url('/{slug}/assets/",
        }
        for old, new in replacements_map.items():
            html_content = html_content.replace(old, new)

    return html_content

@app.route('/')
def index():
    """기본 청첩장으로 리다이렉트"""
    ensure_default_invitation()
    default_slug = get_default_invitation_slug()
    if default_slug:
        return redirect(url_for('invitation_page', slug=default_slug))

    if os.path.exists('index.html'):
        with open('index.html', 'r', encoding='utf-8') as f:
            return f.read()

    return '<h1>작성된 청첩장이 없습니다. 관리자 화면에서 새 청첩장을 생성하세요.</h1>'


@app.route('/<slug>')
def invitation_page(slug):
    ensure_default_invitation()
    if slug in RESERVED_SLUGS:
        abort(404)

    if not invitation_exists(slug):
        abort(404)

    record_visit(slug)
    config = load_config(slug)
    html = generate_invitation_html(config, slug=slug)
    return html

@app.route('/admin')
def admin():
    """관리자 페이지"""
    ensure_default_invitation()
    invitations = list_invitations()
    slug = resolve_invitation_slug()

    if not slug or slug not in {item['slug'] for item in invitations}:
        slug = get_default_invitation_slug()

    config = load_config(slug) if slug else {}
    custom_template_path = get_custom_template_path(slug) if slug else None
    custom_template_exists = bool(custom_template_path and os.path.exists(custom_template_path))

    return render_template_string(
        ADMIN_TEMPLATE,
        config=config,
        invitations=invitations,
        selected_slug=slug,
        default_slug=get_default_invitation_slug(),
        custom_template_exists=custom_template_exists,
        custom_template_path=custom_template_path,
    )

@app.route('/admin/save', methods=['POST'])
def admin_save():
    """관리자 설정 저장"""
    try:
        slug = resolve_invitation_slug()
        if not slug or not invitation_exists(slug):
            flash('선택된 청첩장을 찾을 수 없습니다.', 'error')
            return redirect(url_for('admin'))

        config = load_config(slug)
        config.setdefault('meta', {})
        config['meta'].setdefault('thumbnail', '')
        
        # 웨딩 정보 업데이트
        config["wedding_info"] = {
            "groom_name": request.form.get('groom_name', ''),
            "bride_name": request.form.get('bride_name', ''),
            "wedding_date": request.form.get('wedding_date', ''),
            "wedding_time": request.form.get('wedding_time', ''),
            "wedding_venue": request.form.get('wedding_venue', ''),
            "wedding_address": request.form.get('wedding_address', '')
        }
        
        # 가족 정보 업데이트
        config["family_info"] = {
            "groom_father": request.form.get('groom_father', ''),
            "groom_mother": request.form.get('groom_mother', ''),
            "bride_father": request.form.get('bride_father', ''),
            "bride_mother": request.form.get('bride_mother', '')
        }
        
        # 메시지 업데이트
        config["messages"] = {
            "invitation_message": request.form.get('invitation_message', ''),
            "poem_message": request.form.get('poem_message', ''),
            "outro_message": request.form.get('outro_message', '')
        }
        
        # 교통 정보 업데이트
        config["transportation"] = {
            "subway": request.form.get('subway_info', ''),
            "bus": request.form.get('bus_info', ''),
            "parking": request.form.get('parking_info', '')
        }
        
        # 계좌 정보 초기화
        if "account_info" not in config:
            config["account_info"] = {}
        config["account_info"]["groom_accounts"] = []
        config["account_info"]["bride_accounts"] = []
        
        # 오디오 설정 업데이트 (기존 배경음악 파일은 보존)
        if "audio" not in config:
            config["audio"] = {}

        existing_audio = config["audio"].copy()
        existing_background_music = existing_audio.get("background_music", "")
        update_audio_fields = any(key in request.form for key in ('audio_autoplay', 'audio_loop', 'audio_volume'))

        if update_audio_fields:
            config["audio"]["autoplay"] = 'audio_autoplay' in request.form
            config["audio"]["loop"] = 'audio_loop' in request.form
            config["audio"]["volume"] = int(request.form.get('audio_volume', existing_audio.get('volume', 50)))
        else:
            config["audio"]["autoplay"] = existing_audio.get('autoplay', config["audio"].get('autoplay', False))
            config["audio"]["loop"] = existing_audio.get('loop', config["audio"].get('loop', False))
            config["audio"]["volume"] = existing_audio.get('volume', config["audio"].get('volume', 50))

        if existing_background_music:
            config["audio"]["background_music"] = existing_background_music
        
        # 지도 설정 업데이트
        if "map" not in config:
            config["map"] = {}
        
        # 기존 지도 이미지 경로 보존
        existing_map_image = config["map"].get("image", "")
        if existing_map_image:
            config["map"]["image"] = existing_map_image
        
        # 지도 링크 업데이트
        config["map"]["link"] = request.form.get('map_link', '').strip()
        
        # 계좌 정보 처리
        groom_account_count = int(request.form.get('groom_account_count', 0))
        for i in range(groom_account_count):
            bank = request.form.get(f'groom_bank_{i}', '').strip()
            number = request.form.get(f'groom_number_{i}', '').strip()
            name = request.form.get(f'groom_account_name_{i}', '').strip()
            if bank and number and name:
                config['account_info']['groom_accounts'].append({
                    'bank': bank,
                    'number': number,
                    'name': name
                })
        
        bride_account_count = int(request.form.get('bride_account_count', 0))
        for i in range(bride_account_count):
            bank = request.form.get(f'bride_bank_{i}', '').strip()
            number = request.form.get(f'bride_number_{i}', '').strip()
            name = request.form.get(f'bride_account_name_{i}', '').strip()
            if bank and number and name:
                config['account_info']['bride_accounts'].append({
                    'bank': bank,
                    'number': number,
                    'name': name
                })
        
        # 설정 저장 (config는 이미 기존 설정을 로드하고 업데이트한 상태)
        if not config['meta'].get('name'):
            groom_display = config['wedding_info'].get('groom_name', '').strip() or '신랑'
            bride_display = config['wedding_info'].get('bride_name', '').strip() or '신부'
            config['meta']['name'] = f"{groom_display} ♥ {bride_display}"

        config['meta']['updated_at'] = datetime.utcnow().isoformat()
        save_config(config, invitation_slug=slug)

        sync_invitation_index(slug, config)

        flash('설정이 성공적으로 저장되었습니다!', 'success')
        return redirect(url_for('admin', slug=slug))

    except Exception as e:
        flash(f'저장 중 오류가 발생했습니다: {str(e)}', 'error')
        return redirect(url_for('admin', slug=resolve_invitation_slug()))


@app.route('/admin/template/split', methods=['POST'])
def admin_template_split():
    slug = resolve_invitation_slug()
    if not slug or not invitation_exists(slug):
        flash('선택된 청첩장을 찾을 수 없습니다.', 'error')
        return redirect(url_for('admin'))

    custom_path = get_custom_template_path(slug)
    ensure_invitation_directory(slug)

    if custom_path and os.path.exists(custom_path):
        flash('이미 커스텀 템플릿이 존재합니다.', 'info')
    else:
        try:
            shutil.copyfile('index_template.html', custom_path)
            flash('커스텀 템플릿을 생성했습니다. 파일을 수정하여 맞춤 디자인을 적용하세요.', 'success')
        except OSError as exc:
            flash(f'커스텀 템플릿 생성에 실패했습니다: {exc}', 'error')

    return redirect(url_for('admin', slug=slug))


@app.route('/admin/template/reset', methods=['POST'])
def admin_template_reset():
    slug = resolve_invitation_slug()
    if not slug or not invitation_exists(slug):
        flash('선택된 청첩장을 찾을 수 없습니다.', 'error')
        return redirect(url_for('admin'))

    custom_path = get_custom_template_path(slug)

    if not custom_path or not os.path.exists(custom_path):
        flash('커스텀 템플릿을 찾을 수 없습니다. 이미 기본 템플릿을 사용하고 있습니다.', 'info')
    else:
        try:
            os.remove(custom_path)
            flash('커스텀 템플릿을 삭제하고 기본 템플릿으로 전환했습니다.', 'success')
        except OSError as exc:
            flash(f'커스텀 템플릿 삭제에 실패했습니다: {exc}', 'error')

    return redirect(url_for('admin', slug=slug))

@app.route('/admin/upload_image', methods=['POST'])
def upload_image():
    """이미지/비디오 업로드 (모바일 최적화)"""
    try:
        # 요청 검증
        if 'file' not in request.files:
            app.logger.error('파일이 요청에 포함되지 않음')
            return jsonify({'success': False, 'message': '파일이 선택되지 않았습니다.'})
        
        file = request.files['file']
        image_type = request.form.get('image_type', '')
        thumbnail_uploaded = False
        slug = resolve_invitation_slug()

        if not slug or not invitation_exists(slug):
            return jsonify({'success': False, 'message': '선택된 청첩장을 찾을 수 없습니다.'})

        directories = ensure_invitation_directory(slug)
        
        # 요청 정보 로깅 (모바일 디버깅용)
        file_size = len(file.read())
        file.seek(0)  # 파일 포인터 리셋
        app.logger.info(f'업로드 요청: 파일={file.filename}, 타입={image_type}, 크기={file_size}bytes')
        
        if file.filename == '':
            return jsonify({'success': False, 'message': '파일이 선택되지 않았습니다.'})
        
        # 파일 크기 검증 (100MB 제한)
        if file_size > 100 * 1024 * 1024:
            return jsonify({'success': False, 'message': f'파일이 너무 큽니다. 최대 100MB까지 가능합니다. (현재: {file_size // (1024*1024)}MB)'})
        
        if file and allowed_file(file.filename):
            # 안전한 파일명 생성
            original_filename = file.filename
            filename = secure_filename(original_filename)
            
            # 파일명이 비어있을 경우 타임스탬프로 생성 (모바일에서 종종 발생)
            if not filename:
                file_ext = original_filename.rsplit('.', 1)[1].lower() if '.' in original_filename else 'jpg'
                filename = f'mobile_upload_{int(time.time())}.{file_ext}'
            
            # 타임스탬프 추가 (중복 방지)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_")
            filename = timestamp + filename
            
            # 영상 파일인지 확인
            is_video = is_video_file(file.filename)
            
            # 파일 경로 결정
            if image_type == 'gallery':
                if is_video:
                    filepath = os.path.join(directories['videos'], filename)
                    web_filepath = f'assets/videos/{filename}'
                else:
                    filepath = os.path.join(directories['gallery'], filename)
                    web_filepath = f'assets/images/gallery/{filename}'
            else:
                if is_video:
                    filepath = os.path.join(directories['videos'], filename)
                    web_filepath = f'assets/videos/{filename}'
                else:
                    filepath = os.path.join(directories['images'], filename)
                    web_filepath = f'assets/images/{filename}'

            # 디렉토리 생성 및 확인
            try:
                os.makedirs(os.path.dirname(filepath), exist_ok=True)
                app.logger.info(f'디렉토리 확인/생성 완료: {os.path.dirname(filepath)}')
            except Exception as dir_error:
                app.logger.error(f'디렉토리 생성 실패: {dir_error}')
                return jsonify({'success': False, 'message': f'디렉토리 생성 실패: {str(dir_error)}'})
            
            # 파일 저장
            try:
                file.save(filepath)
                app.logger.info(f'파일 저장 완료: {filepath}')
                
                # 파일이 실제로 저장되었는지 확인
                if not os.path.exists(filepath):
                    raise Exception('파일 저장 후 파일이 존재하지 않음')
                    
                saved_size = os.path.getsize(filepath)
                app.logger.info(f'저장된 파일 크기: {saved_size}bytes')
                
            except Exception as save_error:
                app.logger.error(f'파일 저장 실패: {save_error}')
                return jsonify({'success': False, 'message': f'파일 저장에 실패했습니다: {str(save_error)}'})
            
            # config.json 업데이트
            try:
                config = load_config(slug)

                if image_type == 'gallery':
                    if 'gallery_images' not in config:
                        config['gallery_images'] = []
                    # 새로운 파일을 기본 크기로 추가 (이미지 또는 영상)
                    config['gallery_images'].append({
                        'path': web_filepath,
                        'size': 'small',
                        'type': 'video' if is_video else 'image'
                    })
                else:
                    if 'images' not in config:
                        config['images'] = {}

                    if image_type == 'main':
                        config['images']['main_photo'] = web_filepath
                        config['images']['main_photo_type'] = 'video' if is_video else 'image'
                    elif image_type == 'invitation':
                        config['images']['invitation_photo'] = web_filepath
                        config['images']['invitation_photo_type'] = 'video' if is_video else 'image'
                    elif image_type == 'photobooth':
                        config['images']['photobooth_photo'] = web_filepath
                        config['images']['photobooth_photo_type'] = 'video' if is_video else 'image'
                    elif image_type == 'outro':
                        config['images']['outro_photo'] = web_filepath
                        config['images']['outro_photo_type'] = 'video' if is_video else 'image'
                    elif image_type == 'thumbnail':
                        config.setdefault('meta', {})
                        old_thumbnail = config['meta'].get('thumbnail')
                        if old_thumbnail:
                            old_thumbnail_path = to_invitation_file_path(slug, old_thumbnail)
                            if old_thumbnail_path and os.path.exists(old_thumbnail_path):
                                try:
                                    os.remove(old_thumbnail_path)
                                    app.logger.info(f'기존 썸네일 파일 삭제: {old_thumbnail_path}')
                                except Exception as delete_thumb_error:
                                    app.logger.warning(f'기존 썸네일 파일 삭제 실패: {delete_thumb_error}')
                        config['meta']['thumbnail'] = web_filepath
                        thumbnail_uploaded = True

                config.setdefault('meta', {})['updated_at'] = datetime.utcnow().isoformat()
                save_config(config, invitation_slug=slug)
                if thumbnail_uploaded:
                    sync_invitation_index(slug, config)
                app.logger.info(f'설정 업데이트 완료: {image_type} -> {web_filepath}')

            except Exception as config_error:
                # 파일은 저장되었지만 설정 업데이트 실패 - 파일 삭제
                try:
                    os.remove(filepath)
                    app.logger.info(f'설정 실패로 파일 삭제: {filepath}')
                except:
                    pass
                app.logger.error(f'설정 업데이트 실패: {config_error}')
                return jsonify({'success': False, 'message': f'설정 저장에 실패했습니다: {str(config_error)}'})
            
            media_name = '비디오' if is_video else '이미지'
            success_message = f'{media_name}가 성공적으로 업로드되었습니다.'
            if thumbnail_uploaded:
                success_message = '대표 썸네일이 업로드되었습니다.'
            return jsonify({
                'success': True, 
                'message': success_message,
                'filepath': web_filepath,
                'filename': filename,
                'type': 'video' if is_video else 'image',
                'size': saved_size,
                'slug': slug,
                'asset_type': image_type
            })
            
        else:
            # 허용되지 않는 파일 형식
            allowed_exts = list(ALLOWED_EXTENSIONS) + list(VIDEO_EXTENSIONS)
            return jsonify({
                'success': False, 
                'message': f'허용되지 않는 파일 형식입니다. 지원 형식: {", ".join(allowed_exts)}'
            })
            
    except Exception as e:
        app.logger.error(f'업로드 전체 오류: {e}', exc_info=True)
        return jsonify({'success': False, 'message': f'업로드 중 오류가 발생했습니다: {str(e)}'})

@app.route('/admin/delete_gallery/<int:index>')
def delete_gallery_image(index):
    """갤러리 이미지 삭제"""
    slug = resolve_invitation_slug()
    try:
        
        if not slug or not invitation_exists(slug):
            flash('선택된 청첩장을 찾을 수 없습니다.', 'error')
            return redirect(url_for('admin'))

        config = load_config(slug)
        gallery_images = config.get('gallery_images', [])
        
        if 0 <= index < len(gallery_images):
            # 파일 삭제
            image_data = gallery_images[index]
            if isinstance(image_data, dict):
                image_path = image_data.get('path', '')
            else:
                image_path = image_data
                
            actual_path = to_invitation_file_path(slug, image_path)
            if actual_path and os.path.exists(actual_path):
                os.remove(actual_path)
            
            # config에서 제거
            gallery_images.pop(index)
            config['gallery_images'] = gallery_images
            config.setdefault('meta', {})['updated_at'] = datetime.utcnow().isoformat()
            save_config(config, invitation_slug=slug)
            
            flash('갤러리 이미지가 삭제되었습니다.', 'success')
        else:
            flash('잘못된 이미지 인덱스입니다.', 'error')
            
    except Exception as e:
        flash(f'삭제 중 오류가 발생했습니다: {str(e)}', 'error')
    
    return redirect(url_for('admin', slug=slug))

@app.route('/admin/guestbook')
def admin_guestbook():
    """방명록 관리 페이지"""
    slug = resolve_invitation_slug()
    if slug and not invitation_exists(slug):
        slug = None

    if not slug:
        slug = get_default_invitation_slug()

    try:
        guestbook = load_guestbook_entries(slug)
        guestbook.sort(key=lambda x: x.get('timestamp', 0), reverse=True)
        return render_template_string(
            GUESTBOOK_ADMIN_TEMPLATE,
            guestbook=guestbook,
            current_slug=slug,
            invitations=list_invitations(),
            default_slug=get_default_invitation_slug(),
        )
    except Exception as e:
        flash(f'방명록 로드 중 오류가 발생했습니다: {str(e)}', 'error')
        return redirect(url_for('admin', slug=slug))


@app.route('/admin/rsvp')
def admin_rsvp():
    """RSVP 관리 페이지"""
    slug = resolve_invitation_slug()
    if slug and not invitation_exists(slug):
        slug = None

    if not slug:
        slug = get_default_invitation_slug()

    try:
        raw_entries = load_rsvp_entries(slug)
        raw_entries.sort(key=lambda x: x.get('submitted_at', ''), reverse=True)

        total_entries = len(raw_entries)
        total_attendees = sum(entry.get('attendees', 1) for entry in raw_entries)

        meal_stats = {
            'planned': sum(1 for entry in raw_entries if entry.get('meal') == 'planned'),
            'not_planned': sum(1 for entry in raw_entries if entry.get('meal') == 'not_planned'),
            'undecided': sum(1 for entry in raw_entries if entry.get('meal') not in {'planned', 'not_planned'})
        }

        side_stats = {
            'groom': sum(1 for entry in raw_entries if entry.get('side') == 'groom'),
            'bride': sum(1 for entry in raw_entries if entry.get('side') == 'bride')
        }

        meal_labels = {
            'planned': '예정',
            'not_planned': '미예정',
            'undecided': '미정'
        }

        side_labels = {
            'groom': '신랑측',
            'bride': '신부측'
        }

        display_entries = []
        for entry in raw_entries:
            view = dict(entry)
            submitted_at = entry.get('submitted_at')
            if submitted_at:
                try:
                    submitted_dt = datetime.fromisoformat(submitted_at)
                    view['submitted_display'] = submitted_dt.strftime('%Y-%m-%d %H:%M')
                except ValueError:
                    view['submitted_display'] = submitted_at.replace('T', ' ')[:16]
            else:
                view['submitted_display'] = '-'

            view['meal_display'] = meal_labels.get(entry.get('meal'), '예정')
            view['side_display'] = side_labels.get(entry.get('side'), '신랑측')
            display_entries.append(view)

        return render_template_string(
            RSVP_ADMIN_TEMPLATE,
            rsvp_entries=display_entries,
            invitations=list_invitations(),
            selected_slug=slug,
            default_slug=get_default_invitation_slug(),
            total_entries=total_entries,
            total_attendees=total_attendees,
            meal_stats=meal_stats,
            side_stats=side_stats,
        )
    except Exception as e:
        flash(f'RSVP 데이터를 불러오는 중 오류가 발생했습니다: {str(e)}', 'error')
        return redirect(url_for('admin', slug=slug))


@app.route('/admin/rsvp/delete/<int:entry_id>', methods=['POST'])
def admin_delete_rsvp(entry_id):
    slug = resolve_invitation_slug()
    if slug and not invitation_exists(slug):
        slug = None

    if not slug:
        slug = get_default_invitation_slug()

    if not slug:
        flash('청첩장을 찾을 수 없습니다.', 'error')
        return redirect(url_for('admin_rsvp'))

    try:
        entries = load_rsvp_entries(slug)
        original_length = len(entries)
        entries = [entry for entry in entries if entry.get('id') != entry_id]

        if len(entries) == original_length:
            flash('해당 참석 의사 정보를 찾을 수 없습니다.', 'error')
        else:
            save_rsvp_entries(slug, entries)
            flash('참석 의사 정보가 삭제되었습니다.', 'success')

        return redirect(url_for('admin_rsvp', slug=slug))
    except Exception as e:
        flash(f'삭제 중 오류가 발생했습니다: {str(e)}', 'error')
        return redirect(url_for('admin_rsvp', slug=slug))


@app.route('/admin/visits')
def admin_visits():
    """방문 로그 관리 페이지"""
    slug = resolve_invitation_slug()
    if slug and not invitation_exists(slug):
        slug = None

    if not slug:
        slug = get_default_invitation_slug()

    if not slug:
        flash('청첩장을 찾을 수 없습니다.', 'error')
        return redirect(url_for('admin'))

    try:
        raw_entries = load_visit_entries(slug)
        raw_entries.sort(key=lambda item: item.get('last_seen', ''), reverse=True)

        unique_ip_count = len(raw_entries)
        total_visit_count = sum(entry.get('count') or len(entry.get('visits', [])) for entry in raw_entries)

        now = datetime.utcnow()
        recent_threshold = now - timedelta(hours=24)
        recent_24h_count = 0

        display_entries = []
        for entry in raw_entries:
            visits = entry.get('visits', [])
            sorted_visits = sorted(visits, key=lambda item: item.get('timestamp', ''))

            if sorted_visits:
                first_timestamp = sorted_visits[0].get('timestamp')
                last_timestamp = sorted_visits[-1].get('timestamp')
            else:
                first_timestamp = entry.get('last_seen')
                last_timestamp = entry.get('last_seen')

            def parse_timestamp(value):
                if not value:
                    return None
                try:
                    return datetime.fromisoformat(value.replace('Z', '+00:00'))
                except ValueError:
                    return None

            first_dt = parse_timestamp(first_timestamp)
            last_dt = parse_timestamp(last_timestamp)

            # 최근 24시간 방문 수 집계
            for visit in visits:
                visit_dt = parse_timestamp(visit.get('timestamp'))
                if visit_dt and visit_dt >= recent_threshold:
                    recent_24h_count += 1

            visit_display_items = []
            for visit in sorted(visits, key=lambda item: item.get('timestamp', ''), reverse=True)[:10]:
                visit_dt = parse_timestamp(visit.get('timestamp'))
                visit_display_items.append({
                    'timestamp_display': visit_dt.strftime('%Y-%m-%d %H:%M') if visit_dt else (visit.get('timestamp') or '-'),
                    'path': visit.get('path', '-')
                })

            entry_view = {
                'ip': entry.get('ip', 'unknown'),
                'count': entry.get('count') or len(visits),
                'last_seen_display': last_dt.strftime('%Y-%m-%d %H:%M') if last_dt else '-',
                'first_seen_display': first_dt.strftime('%Y-%m-%d %H:%M') if first_dt else '-',
                'last_path': entry.get('last_path', '-'),
                'user_agents': entry.get('user_agents', []),
                'visits': visit_display_items,
            }
            display_entries.append(entry_view)

        return render_template_string(
            VISITS_ADMIN_TEMPLATE,
            visit_entries=display_entries,
            invitations=list_invitations(),
            selected_slug=slug,
            default_slug=get_default_invitation_slug(),
            unique_ip_count=unique_ip_count,
            total_visit_count=total_visit_count,
            recent_24h_count=recent_24h_count,
        )
    except Exception as e:
        app.logger.error(f'방문 로그 로드 오류: {e}', exc_info=True)
        flash(f'방문 로그를 불러오는 중 오류가 발생했습니다: {str(e)}', 'error')
        return redirect(url_for('admin', slug=slug))


@app.route('/admin/visits/delete', methods=['POST'])
def admin_delete_visit_entry():
    slug = resolve_invitation_slug()
    if slug and not invitation_exists(slug):
        slug = None

    if not slug:
        slug = get_default_invitation_slug()

    if not slug:
        flash('청첩장을 찾을 수 없습니다.', 'error')
        return redirect(url_for('admin_visits'))

    ip = (request.form.get('ip') or '').strip()
    if not ip:
        flash('IP 정보가 제공되지 않았습니다.', 'error')
        return redirect(url_for('admin_visits', slug=slug))

    try:
        entries = load_visit_entries(slug)
        new_entries = [entry for entry in entries if entry.get('ip') != ip]

        if len(new_entries) == len(entries):
            flash('해당 IP의 로그를 찾을 수 없습니다.', 'error')
        else:
            save_visit_entries(slug, new_entries)
            flash('선택한 IP의 방문 로그를 삭제했습니다.', 'success')

        return redirect(url_for('admin_visits', slug=slug))
    except Exception as e:
        flash(f'삭제 중 오류가 발생했습니다: {str(e)}', 'error')
        return redirect(url_for('admin_visits', slug=slug))


@app.route('/admin/visits/clear', methods=['POST'])
def admin_clear_visits():
    slug = resolve_invitation_slug()
    if slug and not invitation_exists(slug):
        slug = None

    if not slug:
        slug = get_default_invitation_slug()

    if not slug:
        flash('청첩장을 찾을 수 없습니다.', 'error')
        return redirect(url_for('admin_visits'))

    try:
        save_visit_entries(slug, [])
        flash('방문 로그를 초기화했습니다.', 'success')
    except Exception as e:
        flash(f'초기화 중 오류가 발생했습니다: {str(e)}', 'error')

    return redirect(url_for('admin_visits', slug=slug))

@app.route('/admin/guestbook/delete/<int:entry_id>', methods=['POST'])
def admin_delete_guestbook(entry_id):
    """관리자 방명록 삭제"""
    slug = resolve_invitation_slug()
    if slug and not invitation_exists(slug):
        slug = None

    if not slug:
        slug = get_default_invitation_slug()

    try:
        guestbook = load_guestbook_entries(slug)
        guestbook = [entry for entry in guestbook if entry['id'] != entry_id]
        save_guestbook_entries(slug, guestbook)

        flash('방명록이 삭제되었습니다.', 'success')

    except Exception as e:
        flash(f'삭제 중 오류가 발생했습니다: {str(e)}', 'error')

    return redirect(url_for('admin_guestbook', slug=slug))

@app.route('/api/image_urls')
def get_image_urls():
    """프리로딩을 위한 모든 이미지 URL 목록 반환"""
    try:
        slug = resolve_invitation_slug()
        if slug and not invitation_exists(slug):
            slug = None

        if not slug:
            slug = get_default_invitation_slug()

        config = load_config(slug) if slug else {}
        image_urls = []

        def url_for_asset(path_value):
            if not path_value:
                return None
            path_value = str(path_value)
            if path_value.startswith(('http://', 'https://', '//')):
                return path_value
            normalized = path_value.lstrip('/')
            if slug:
                return f'/{slug}/{normalized}'
            return f'/{normalized}'

        images = config.get('images', {})
        for key, path in images.items():
            resolved = url_for_asset(path)
            if resolved:
                image_urls.append(resolved)

        gallery_images = config.get('gallery_images', [])
        for image_data in gallery_images:
            if isinstance(image_data, dict):
                resolved = url_for_asset(image_data.get('path'))
            else:
                resolved = url_for_asset(image_data)
            if resolved:
                image_urls.append(resolved)

        map_image = config.get('map', {}).get('image')
        resolved_map = url_for_asset(map_image)
        if resolved_map:
            image_urls.append(resolved_map)

        return jsonify({'success': True, 'images': image_urls, 'slug': slug})

    except Exception as e:
        return jsonify({'success': False, 'message': f'이미지 목록을 불러오는 중 오류가 발생했습니다: {str(e)}'})

@app.route('/admin/save_audio_settings', methods=['POST'])
def save_audio_settings():
    """배경음악 설정 저장"""
    try:
        # 폼 데이터에서 설정값 가져오기
        autoplay = 'audio_autoplay' in request.form and request.form['audio_autoplay'] == '1'
        loop = 'audio_loop' in request.form and request.form['audio_loop'] == '1'
        volume = int(request.form.get('audio_volume', 50))
        
        app.logger.info(f'배경음악 설정 저장 요청: autoplay={autoplay}, loop={loop}, volume={volume}')

        slug = resolve_invitation_slug()
        if not slug or not invitation_exists(slug):
            return jsonify({'success': False, 'message': '선택된 청첩장을 찾을 수 없습니다.'})

        # 기존 설정 로드
        config = load_config(slug)
        
        # audio 섹션이 없으면 생성
        if 'audio' not in config:
            config['audio'] = {}
        
        # 설정 업데이트
        config['audio']['autoplay'] = autoplay
        config['audio']['loop'] = loop
        config['audio']['volume'] = volume

        # 설정 저장
        config.setdefault('meta', {})['updated_at'] = datetime.utcnow().isoformat()
        save_config(config, invitation_slug=slug)

        app.logger.info('배경음악 설정 저장 완료')
        
        return jsonify({
            'success': True,
            'message': '배경음악 설정이 저장되었습니다.',
            'settings': {
                'autoplay': autoplay,
                'loop': loop,
                'volume': volume,
                'slug': slug
            }
        })
        
    except Exception as e:
        app.logger.error(f'배경음악 설정 저장 오류: {e}', exc_info=True)
        return jsonify({'success': False, 'message': f'설정 저장 중 오류가 발생했습니다: {str(e)}'})

@app.route('/admin/upload_map', methods=['POST'])
def upload_map():
    """지도 이미지 업로드"""
    slug = resolve_invitation_slug()
    file_path = None
    try:
        if not slug or not invitation_exists(slug):
            return jsonify({'success': False, 'message': '선택된 청첩장을 찾을 수 없습니다.'})

        if 'file' not in request.files:
            app.logger.error('지도 이미지가 요청에 포함되지 않음')
            return jsonify({'success': False, 'message': '파일이 선택되지 않았습니다.'})

        file = request.files['file']
        if file.filename == '':
            app.logger.error('지도 파일명이 비어있음')
            return jsonify({'success': False, 'message': '파일이 선택되지 않았습니다.'})

        file.seek(0, 2)
        file_size = file.tell()
        file.seek(0)

        if file_size > 10 * 1024 * 1024:
            app.logger.error(f'지도 파일 크기 초과: {file_size} bytes')
            return jsonify({'success': False, 'message': '파일 크기가 10MB를 초과합니다.'})

        timestamp = int(time.time())
        original_filename = secure_filename(file.filename)
        if not original_filename:
            file_extension = file.filename.split('.')[-1] if '.' in file.filename else 'jpg'
            original_filename = f"map_{timestamp}.{file_extension}"
        else:
            original_filename = f"{timestamp}_{original_filename}"

        directories = ensure_invitation_directory(slug)
        map_dir = directories['images']
        os.makedirs(map_dir, exist_ok=True)

        file_path = os.path.join(map_dir, original_filename)
        relative_path = f"assets/images/{original_filename}"

        try:
            file.save(file_path)
            app.logger.info(f'지도 이미지 저장 완료: {file_path}')
        except Exception as e:
            app.logger.error(f'지도 파일 저장 실패: {e}')
            return jsonify({'success': False, 'message': '파일 저장 중 오류가 발생했습니다.'})

        try:
            config = load_config(slug)
            if 'map' not in config:
                config['map'] = {}

            old_file_path = to_invitation_file_path(slug, config['map'].get('image')) if config['map'].get('image') else None
            if old_file_path and os.path.exists(old_file_path):
                try:
                    os.remove(old_file_path)
                    app.logger.info(f'기존 지도 이미지 삭제: {old_file_path}')
                except Exception as e:
                    app.logger.warning(f'기존 지도 이미지 삭제 실패: {e}')

            config['map']['image'] = relative_path
            config.setdefault('meta', {})['updated_at'] = datetime.utcnow().isoformat()
            save_config(config, invitation_slug=slug)
            app.logger.info('지도 설정 업데이트 완료')

        except Exception as e:
            app.logger.error(f'지도 설정 업데이트 실패: {e}')
            if file_path and os.path.exists(file_path):
                os.remove(file_path)
            return jsonify({'success': False, 'message': '설정 업데이트 중 오류가 발생했습니다.'})

        return jsonify({
            'success': True,
            'message': '지도 이미지가 업로드되었습니다.',
            'file_path': relative_path,
            'slug': slug
        })

    except Exception as e:
        app.logger.error(f'지도 업로드 전체 오류: {e}', exc_info=True)
        if file_path and os.path.exists(file_path):
            os.remove(file_path)
        return jsonify({'success': False, 'message': f'업로드 중 오류가 발생했습니다: {str(e)}'})

@app.route('/admin/upload_audio', methods=['POST'])
def upload_audio():
    """오디오 파일 업로드"""
    slug = resolve_invitation_slug()
    file_path = None
    try:
        if not slug or not invitation_exists(slug):
            return jsonify({'success': False, 'message': '선택된 청첩장을 찾을 수 없습니다.'})

        if 'file' not in request.files:
            app.logger.error('오디오 파일이 요청에 포함되지 않음')
            return jsonify({'success': False, 'message': '파일이 선택되지 않았습니다.'})

        file = request.files['file']
        audio_type = request.form.get('audio_type', 'background')

        file_size = len(file.read())
        file.seek(0)
        app.logger.info(f'오디오 업로드 요청: 파일={file.filename}, 타입={audio_type}, 크기={file_size}bytes')

        if file.filename == '':
            return jsonify({'success': False, 'message': '파일이 선택되지 않았습니다.'})

        if file_size > 100 * 1024 * 1024:
            return jsonify({'success': False, 'message': f'파일이 너무 큽니다. 최대 100MB까지 가능합니다. (현재: {file_size // (1024*1024)}MB)'})

        if not is_audio_file(file.filename):
            allowed_exts = ', '.join(sorted(AUDIO_EXTENSIONS))
            return jsonify({'success': False, 'message': f'허용되지 않는 오디오 파일 형식입니다. 지원 형식: {allowed_exts}'})

        original_filename = file.filename
        filename = secure_filename(original_filename)
        if not filename:
            file_ext = original_filename.rsplit('.', 1)[1].lower() if '.' in original_filename else 'mp3'
            filename = f'background_music_{int(time.time())}.{file_ext}'

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_")
        filename = timestamp + filename

        directories = ensure_invitation_directory(slug)
        audio_dir = directories['audio']
        os.makedirs(audio_dir, exist_ok=True)

        file_path = os.path.join(audio_dir, filename)
        web_filepath = f'assets/audio/{filename}'

        try:
            file.save(file_path)
            if not os.path.exists(file_path):
                raise Exception('파일 저장 후 파일이 존재하지 않음')
            saved_size = os.path.getsize(file_path)
            app.logger.info(f'오디오 파일 저장 완료: {file_path}')
        except Exception as save_error:
            if file_path and os.path.exists(file_path):
                os.remove(file_path)
            app.logger.error(f'오디오 파일 저장 실패: {save_error}')
            return jsonify({'success': False, 'message': f'파일 저장에 실패했습니다: {str(save_error)}'})

        try:
            config = load_config(slug)
            if 'audio' not in config:
                config['audio'] = {}

            target_key = 'background_music' if audio_type == 'background' else f'{audio_type}_music'

            old_path = to_invitation_file_path(slug, config['audio'].get(target_key))
            if old_path and os.path.exists(old_path):
                try:
                    os.remove(old_path)
                    app.logger.info(f'기존 오디오 파일 삭제: {old_path}')
                except Exception as delete_error:
                    app.logger.warning(f'기존 오디오 파일 삭제 실패: {delete_error}')

            config['audio'][target_key] = web_filepath
            config['audio'].setdefault('autoplay', True)
            config['audio'].setdefault('loop', True)
            config['audio'].setdefault('volume', 50)
            config.setdefault('meta', {})['updated_at'] = datetime.utcnow().isoformat()
            save_config(config, invitation_slug=slug)
            app.logger.info(f'오디오 설정 업데이트 완료: {web_filepath}')

        except Exception as config_error:
            if file_path and os.path.exists(file_path):
                os.remove(file_path)
            app.logger.error(f'오디오 설정 업데이트 실패: {config_error}')
            return jsonify({'success': False, 'message': f'설정 저장에 실패했습니다: {str(config_error)}'})

        return jsonify({
            'success': True,
            'message': '배경음악이 성공적으로 업로드되었습니다.',
            'filepath': web_filepath,
            'filename': filename,
            'size': saved_size,
            'slug': slug
        })

    except Exception as e:
        app.logger.error(f'오디오 업로드 전체 오류: {e}', exc_info=True)
        if file_path and os.path.exists(file_path):
            os.remove(file_path)
        return jsonify({'success': False, 'message': f'업로드 중 오류가 발생했습니다: {str(e)}'})

@app.route('/admin/add_url_thumbnail', methods=['POST'])
def add_url_thumbnail():
    """URL 썸네일 추가"""
    try:
        data = request.json or {}
        url = data.get('url', '').strip()
        size = data.get('size', 'small')
        media_type = data.get('type', 'url_image')
        slug = resolve_invitation_slug()

        if not slug or not invitation_exists(slug):
            return jsonify({'success': False, 'message': '선택된 청첩장을 찾을 수 없습니다.'})

        if not url:
            return jsonify({'success': False, 'message': 'URL이 필요합니다.'})

        if not url.startswith(('http://', 'https://')):
            return jsonify({'success': False, 'message': '올바른 URL 형식이 아닙니다.'})

        config = load_config(slug)

        if 'gallery_images' not in config:
            config['gallery_images'] = []

        config['gallery_images'].append({
            'path': url,
            'size': size,
            'type': media_type
        })

        config.setdefault('meta', {})['updated_at'] = datetime.utcnow().isoformat()
        save_config(config, invitation_slug=slug)

        return jsonify({
            'success': True,
            'message': 'URL 썸네일이 추가되었습니다.',
            'url': url,
            'slug': slug
        })

    except Exception as e:
        return jsonify({'success': False, 'message': f'추가 중 오류가 발생했습니다: {str(e)}'})


@app.route('/admin/set_thumbnail_url', methods=['POST'])
def set_thumbnail_url():
    """대표 썸네일을 URL로 설정"""
    try:
        data = request.json or {}
        url = (data.get('url') or '').strip()
        slug = resolve_invitation_slug()

        if not slug or not invitation_exists(slug):
            return jsonify({'success': False, 'message': '선택된 청첩장을 찾을 수 없습니다.'})

        if not url:
            return jsonify({'success': False, 'message': 'URL이 필요합니다.'})

        if not (url.startswith(('http://', 'https://', '//', '/')) or url.startswith('assets/')):
            return jsonify({'success': False, 'message': '올바른 URL 형식이 아닙니다.'})

        config = load_config(slug)
        config.setdefault('meta', {})

        current_thumbnail = config['meta'].get('thumbnail')
        if current_thumbnail and current_thumbnail != url:
            old_path = to_invitation_file_path(slug, current_thumbnail)
            if old_path and os.path.exists(old_path):
                try:
                    os.remove(old_path)
                    app.logger.info(f'기존 썸네일 파일 삭제: {old_path}')
                except Exception as delete_error:
                    app.logger.warning(f'기존 썸네일 파일 삭제 실패: {delete_error}')

        config['meta']['thumbnail'] = url
        config['meta']['updated_at'] = datetime.utcnow().isoformat()
        save_config(config, invitation_slug=slug)
        sync_invitation_index(slug, config)

        return jsonify({'success': True, 'message': '대표 썸네일이 설정되었습니다.', 'thumbnail': url, 'slug': slug})

    except Exception as e:
        return jsonify({'success': False, 'message': f'설정 중 오류가 발생했습니다: {str(e)}'})


@app.route('/admin/thumbnail', methods=['DELETE'])
def delete_thumbnail():
    """대표 썸네일 삭제"""
    try:
        slug = resolve_invitation_slug()

        if not slug or not invitation_exists(slug):
            return jsonify({'success': False, 'message': '선택된 청첩장을 찾을 수 없습니다.'})

        config = load_config(slug)
        meta = config.get('meta', {})
        current_thumbnail = meta.get('thumbnail')

        if current_thumbnail:
            old_path = to_invitation_file_path(slug, current_thumbnail)
            if old_path and os.path.exists(old_path):
                try:
                    os.remove(old_path)
                    app.logger.info(f'대표 썸네일 파일 삭제: {old_path}')
                except Exception as delete_error:
                    app.logger.warning(f'대표 썸네일 파일 삭제 실패: {delete_error}')

        config.setdefault('meta', {})
        config['meta'].pop('thumbnail', None)
        config['meta']['updated_at'] = datetime.utcnow().isoformat()
        save_config(config, invitation_slug=slug)
        sync_invitation_index(slug, config)

        return jsonify({'success': True, 'message': '대표 썸네일이 삭제되었습니다.', 'slug': slug})

    except Exception as e:
        return jsonify({'success': False, 'message': f'삭제 중 오류가 발생했습니다: {str(e)}'})

@app.route('/admin/save_gallery_order', methods=['POST'])
def save_gallery_order():
    """갤러리 순서 및 크기 저장"""
    try:
        data = request.json or {}
        gallery_data = data.get('gallery_data', [])
        slug = resolve_invitation_slug()

        if not slug or not invitation_exists(slug):
            return jsonify({'success': False, 'message': '선택된 청첩장을 찾을 수 없습니다.'})

        config = load_config(slug)
        config['gallery_images'] = gallery_data
        config.setdefault('meta', {})['updated_at'] = datetime.utcnow().isoformat()
        save_config(config, invitation_slug=slug)

        return jsonify({'success': True, 'message': '갤러리 순서와 크기가 저장되었습니다.', 'slug': slug})

    except Exception as e:
        return jsonify({'success': False, 'message': f'저장 중 오류가 발생했습니다: {str(e)}'})


@app.route('/admin/invitations', methods=['GET'])
def list_invitations_api():
    index = load_invitations_index()
    return jsonify({
        'success': True,
        'default_slug': index.get('default_slug'),
        'invitations': list_invitations()
    })


@app.route('/admin/invitations', methods=['POST'])
def create_invitation_api():
    data = request.get_json() or {}
    name = (data.get('name') or '새로운 청첩장').strip() or '새로운 청첩장'
    requested_slug = data.get('slug')
    copy_from = (data.get('copy_from') or '').strip() or None
    make_default = bool(data.get('make_default'))

    source_config = None
    if copy_from and invitation_exists(copy_from):
        source_config = load_config(copy_from)

    created = create_invitation(name, slug=requested_slug, source_config=source_config, make_default=make_default, copy_from_slug=copy_from if copy_from and invitation_exists(copy_from) else None)

    response_data = {
        'success': True,
        'invitation': {
            'slug': created['slug'],
            'name': created['config'].get('meta', {}).get('name', name),
            'created_at': created['config'].get('meta', {}).get('created_at'),
            'updated_at': created['config'].get('meta', {}).get('updated_at'),
        },
        'default_slug': load_invitations_index().get('default_slug')
    }

    return jsonify(response_data), 201


@app.route('/admin/invitations/<slug>', methods=['PATCH'])
def update_invitation_api(slug):
    data = request.get_json() or {}
    updates = {}

    try:
        if 'new_slug' in data:
            new_slug_value = data.get('new_slug')
            renamed_slug = rename_invitation_slug(slug, new_slug_value)
            if renamed_slug != slug:
                updates['slug'] = renamed_slug
                slug = renamed_slug
            updates['default_slug'] = load_invitations_index().get('default_slug')

        if data.get('name'):
            new_name = data['name'].strip() if isinstance(data['name'], str) else ''
            if not new_name:
                return jsonify({'success': False, 'message': '유효한 이름을 입력해주세요.'}), 400
            config = update_invitation_meta(slug, name=new_name)
            updates['name'] = config.get('meta', {}).get('name')
            updates['updated_at'] = config.get('meta', {}).get('updated_at')

        if data.get('set_default'):
            set_default_invitation(slug)
            updates['default_slug'] = load_invitations_index().get('default_slug')

        return jsonify({'success': True, 'updates': updates})

    except ValueError as exc:
        return jsonify({'success': False, 'message': str(exc)}), 400


@app.route('/admin/invitations/<slug>', methods=['DELETE'])
def delete_invitation_api(slug):
    try:
        index = delete_invitation(slug)
        return jsonify({'success': True, 'default_slug': index.get('default_slug'), 'invitations': list_invitations()})
    except ValueError as exc:
        return jsonify({'success': False, 'message': str(exc)}), 400


@app.route('/admin/invitations/<slug>/set-default', methods=['POST'])
def set_default_invitation_api(slug):
    try:
        index = set_default_invitation(slug)
        return jsonify({'success': True, 'default_slug': index.get('default_slug')})
    except ValueError as exc:
        return jsonify({'success': False, 'message': str(exc)}), 400

# 초대장별 에셋 제공
@app.route('/<slug>/assets/<path:filename>')
def invitation_assets(slug, filename):
    if slug in RESERVED_SLUGS:
        abort(404)

    if not invitation_exists(slug):
        abort(404)

    assets_root = os.path.join(INVITATIONS_DIR, slug, 'assets')
    requested_path = os.path.join(assets_root, filename)

    if os.path.exists(requested_path):
        return send_from_directory(assets_root, filename)

    return send_from_directory('assets', filename)

# 기존 라우트들
@app.route('/assets/<path:filename>')
def assets(filename):
    return send_from_directory('assets', filename)

@app.route('/assets/css/<path:filename>')
def css(filename):
    return send_from_directory('assets/css', filename)

@app.route('/assets/js/<path:filename>')
def js(filename):
    return send_from_directory('assets/js', filename)

@app.route('/assets/images/<path:filename>')
def images(filename):
    return send_from_directory('assets/images', filename)

@app.route('/assets/images/gallery/<path:filename>')
def gallery(filename):
    return send_from_directory('assets/images/gallery', filename)

@app.route('/assets/audio/<path:filename>')
def audio(filename):
    return send_from_directory('assets/audio', filename)

@app.route('/assets/videos/<path:filename>')
def videos(filename):
    return send_from_directory('assets/videos', filename)

# 관리자 페이지 HTML 템플릿
ADMIN_TEMPLATE = '''
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>결혼식 청첩장 관리자</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: 'Malgun Gothic', sans-serif; background: #f5f5f5; }
        .container { max-width: 1200px; margin: 0 auto; padding: 20px; }
        .header { background: white; padding: 20px; margin-bottom: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .header h1 { color: #333; }
        .header p { color: #666; margin-top: 10px; }
        .invitation-controls { display: flex; flex-wrap: wrap; gap: 10px; margin-top: 15px; align-items: center; }
        .invitation-controls select { padding: 10px; border: 1px solid #ddd; border-radius: 4px; font-size: 14px; min-width: 220px; }
        .invitation-controls { display: flex; flex-wrap: wrap; gap: 10px; margin-top: 15px; align-items: center; }
        .invitation-controls select { padding: 10px; border: 1px solid #ddd; border-radius: 4px; font-size: 14px; min-width: 220px; }
        .invitation-controls label { font-weight: bold; color: #555; }
        .template-status { margin-top: 10px; display: flex; flex-wrap: wrap; gap: 10px; align-items: center; }
        .template-status span.status { font-weight: bold; color: #333; }
        .template-status form { display: inline; }
        .template-hint { margin-top: 6px; color: #666; font-size: 13px; }
        .section { background: white; margin-bottom: 20px; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .section h2 { color: #333; margin-bottom: 15px; padding-bottom: 10px; border-bottom: 2px solid #eee; }
        .form-group { margin-bottom: 15px; }
        .form-group label { display: block; margin-bottom: 5px; font-weight: bold; color: #555; }
        .form-group input, .form-group textarea { width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 4px; font-size: 14px; }
        .form-group textarea { height: 100px; resize: vertical; }
        .form-row { display: flex; gap: 15px; }
        .form-row .form-group { flex: 1; }
        .btn { padding: 10px 20px; background: #007bff; color: white; border: none; border-radius: 4px; cursor: pointer; font-size: 14px; }
        .btn:hover { background: #0056b3; }
        .btn-danger { background: #dc3545; }
        .btn-danger:hover { background: #c82333; }
        .btn-success { background: #28a745; }
        .btn-success:hover { background: #218838; }
        .image-upload { border: 2px dashed #ddd; padding: 20px; text-align: center; border-radius: 4px; margin-top: 10px; }
        .image-upload:hover { border-color: #007bff; }
        .alert { padding: 10px 15px; margin-bottom: 20px; border-radius: 4px; }
        .alert-success { background: #d4edda; color: #155724; border: 1px solid #c3e6cb; }
        .alert-error { background: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; }
        .preview-btn { margin-left: 10px; background: #17a2b8; }
        .preview-btn:hover { background: #138496; }
        .account-row { margin-bottom: 15px; padding: 15px; background: #f8f9fa; border-radius: 4px; }
        .current-image { max-width: 200px; max-height: 150px; border-radius: 4px; margin-top: 10px; }
        .image-preview { text-align: center; margin-top: 10px; }
        .no-image { color: #666; font-style: italic; }
        .gallery-item { position: relative; background: #f0f0f0; border-radius: 8px; overflow: hidden; cursor: move; transition: transform 0.2s, box-shadow 0.2s; border: 4px solid #fff; }
        .gallery-item:hover { transform: scale(1.02); box-shadow: 0 4px 8px rgba(0,0,0,0.2); }
        .gallery-item.dragging { opacity: 0.5; transform: rotate(2deg); }
        .gallery-item.drag-over { border-color: #007bff; }
        .gallery-item img, .gallery-item video { width: 100%; height: 100%; object-fit: cover; }
        .gallery-video { background: #000; }
        .video-indicator { position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); font-size: 24px; opacity: 0.8; pointer-events: none; }
        .url-indicator { position: absolute; top: 8px; left: 8px; background: rgba(0, 123, 255, 0.9); color: white; padding: 2px 6px; border-radius: 3px; font-size: 10px; pointer-events: none; }
        .gallery-controls { position: absolute; top: 8px; right: 8px; display: flex; gap: 5px; opacity: 0; transition: opacity 0.2s; }
        .gallery-item:hover .gallery-controls { opacity: 1; }
        .control-btn { background: rgba(220, 53, 69, 0.9); color: white; border: none; border-radius: 50%; width: 24px; height: 24px; cursor: pointer; font-size: 14px; display: flex; align-items: center; justify-content: center; font-weight: bold; }
        .control-btn:hover { background: rgba(220, 53, 69, 1); }
        .size-controls { position: absolute; bottom: 8px; left: 8px; display: flex; gap: 4px; opacity: 0; transition: opacity 0.2s; }
        .gallery-item:hover .size-controls { opacity: 1; }
        .size-btn { background: rgba(0,0,0,0.8); color: white; border: none; border-radius: 3px; padding: 4px 6px; font-size: 10px; cursor: pointer; }
        .size-btn:hover { background: rgba(0,0,0,1); }
        .size-btn.active { background: #007bff; }
        .gallery-item.size-small { aspect-ratio: 16/10; }
        .gallery-item.size-tall { aspect-ratio: 16/20; }
        .gallery-grid { display: grid; grid-template-columns: repeat(2, 1fr); grid-auto-rows: auto; gap: 8px; margin-top: 15px; max-width: 600px; }

        .floating-save-container {
            position: fixed;
            top: 15px;
            right: 25px;
            z-index: 1000;
        }
        .floating-save-container .btn-save-all {
            background-color: #007bff;
            color: white;
            padding: 12px 24px;
            border-radius: 50px;
            font-size: 16px;
            font-weight: bold;
            box-shadow: 0 4px 12px rgba(0,0,0,0.2);
            border: none;
            cursor: pointer;
            transition: all 0.2s ease-in-out;
        }
        .floating-save-container .btn-save-all:hover {
            transform: translateY(-2px);
            box-shadow: 0 6px 16px rgba(0,0,0,0.25);
        }
    </style>
</head>
<body>
    <div class="floating-save-container">
        <button type="button" id="floating-save-btn" class="btn-save-all">💾 설정 저장</button>
    </div>

    <div class="container">
        <div class="header">
            <h1>🎊 결혼식 청첩장 관리자</h1>
            <p>청첩장의 모든 정보와 이미지를 쉽게 수정할 수 있습니다.</p>
            <div class="invitation-controls">
                <label for="invitation-select">청첩장 선택</label>
                <select id="invitation-select">
                    {% for invitation in invitations %}
                    <option value="{{ invitation.slug }}" {% if invitation.slug == selected_slug %}selected{% endif %}>{{ invitation.name or invitation.slug }}{% if invitation.slug == default_slug %} (기본){% endif %}</option>
                    {% endfor %}
                </select>
                <button type="button" class="btn" id="create-invitation-btn">➕ 새 청첩장</button>
                <button type="button" class="btn" id="duplicate-invitation-btn">🗂 복제</button>
                <button type="button" class="btn" id="rename-invitation-btn">✏️ 이름 변경</button>
                <button type="button" class="btn" id="rename-slug-btn">📁 주소 변경</button>
                <button type="button" class="btn" id="set-default-btn" {% if selected_slug == default_slug %}disabled{% endif %}>⭐ 기본 지정</button>
                <button type="button" class="btn btn-danger" id="delete-invitation-btn" {% if invitations|length <= 1 %}disabled{% endif %}>🗑 삭제</button>
                <a id="preview-link" href="/{{ (selected_slug or '') }}" class="btn preview-btn" target="_blank">📱 현재 청첩장 보기</a>
                <a href="/admin/guestbook" class="btn" style="background: #6f42c1;">💬 방명록 관리</a>
                <a href="/admin/rsvp" class="btn" style="background: #2f855a;">📝 참석 관리</a>
                <a href="/admin/visits" class="btn" style="background: #dd6b20;">👣 방문 로그</a>
                <a href="/admin/logout" class="btn btn-danger" style="background: #c53030;">🔓 로그아웃</a>
            </div>
            <div class="template-status">
                <span class="status">템플릿 상태: {% if custom_template_exists %}커스텀 템플릿 사용 중{% else %}기본 템플릿 사용{% endif %}</span>
                <form method="POST" action="/admin/template/split">
                    <input type="hidden" name="invitation_slug" value="{{ selected_slug }}">
                    <button type="submit" class="btn btn-secondary" {% if custom_template_exists or not selected_slug %}disabled{% endif %}>커스텀 템플릿 생성</button>
                </form>
                <form method="POST" action="/admin/template/reset">
                    <input type="hidden" name="invitation_slug" value="{{ selected_slug }}">
                    <button type="submit" class="btn btn-danger" {% if not custom_template_exists %}disabled{% endif %}>기본 템플릿 사용</button>
                </form>
            </div>
            <div class="template-hint">
                {% if custom_template_exists %}
                경로: {{ custom_template_path }} 파일을 수정하면 이 청첩장에 적용됩니다.
                {% else %}
                현재 기본 템플릿을 사용 중입니다. 커스텀 템플릿 생성 버튼을 누르면 분리된 파일이 만들어집니다.
                {% endif %}
            </div>
        </div>

        {% with messages = get_flashed_messages(with_categories=true) %}
            {% if messages %}
                {% for category, message in messages %}
                    <div class="alert alert-{{ 'success' if category == 'success' else 'error' }}">
                        {{ message }}
                    </div>
                {% endfor %}
            {% endif %}
        {% endwith %}

        <form method="POST" action="/admin/save" id="admin-form">
            <input type="hidden" name="invitation_slug" value="{{ selected_slug or '' }}">
            <!-- 기본 정보 -->
            <div class="section">
                <h2>💑 기본 정보</h2>
                <div class="form-row">
                    <div class="form-group">
                        <label>신랑 이름</label>
                        <input type="text" name="groom_name" value="{{ config.wedding_info.groom_name or '' }}">
                    </div>
                    <div class="form-group">
                        <label>신부 이름</label>
                        <input type="text" name="bride_name" value="{{ config.wedding_info.bride_name or '' }}">
                    </div>
                </div>
                <div class="form-row">
                    <div class="form-group">
                        <label>결혼식 날짜</label>
                        <input type="date" name="wedding_date" value="{{ config.wedding_info.wedding_date or '' }}">
                    </div>
                    <div class="form-group">
                        <label>결혼식 시간</label>
                        <input type="text" name="wedding_time" value="{{ config.wedding_info.wedding_time or '' }}" placeholder="예: 오후 1시 30분">
                    </div>
                </div>
                <div class="form-row">
                    <div class="form-group">
                        <label>예식장 이름</label>
                        <input type="text" name="wedding_venue" value="{{ config.wedding_info.wedding_venue or '' }}">
                    </div>
                    <div class="form-group">
                        <label>예식장 주소</label>
                        <input type="text" name="wedding_address" value="{{ config.wedding_info.wedding_address or '' }}">
                    </div>
                </div>
            </div>

            <!-- 가족 정보 -->
            <div class="section">
                <h2>👨‍👩‍👧‍👦 가족 정보</h2>
                <div class="form-row">
                    <div class="form-group">
                        <label>신랑 아버지</label>
                        <input type="text" name="groom_father" value="{{ config.family_info.groom_father or '' }}">
                    </div>
                    <div class="form-group">
                        <label>신랑 어머니</label>
                        <input type="text" name="groom_mother" value="{{ config.family_info.groom_mother or '' }}">
                    </div>
                </div>
                <div class="form-row">
                    <div class="form-group">
                        <label>신부 아버지</label>
                        <input type="text" name="bride_father" value="{{ config.family_info.bride_father or '' }}">
                    </div>
                    <div class="form-group">
                        <label>신부 어머니</label>
                        <input type="text" name="bride_mother" value="{{ config.family_info.bride_mother or '' }}">
                    </div>
                </div>
            </div>

            <!-- 메시지 -->
            <div class="section">
                <h2>💌 메시지</h2>
                <div class="form-group">
                    <label>초대 메시지</label>
                    <textarea name="invitation_message">{{ config.messages.invitation_message or '' }}</textarea>
                </div>
                <div class="form-group">
                    <label>시 구절</label>
                    <textarea name="poem_message">{{ config.messages.poem_message or '' }}</textarea>
                </div>
                <div class="form-group">
                    <label>마무리 메시지</label>
                    <textarea name="outro_message">{{ config.messages.outro_message or '' }}</textarea>
                </div>
            </div>

            <!-- 교통 정보 -->
            <div class="section">
                <h2>🚇 교통 정보</h2>
                <div class="form-group">
                    <label>지하철 정보</label>
                    <textarea name="subway_info">{{ config.transportation.subway or '' }}</textarea>
                </div>
                <div class="form-group">
                    <label>버스 정보</label>
                    <textarea name="bus_info">{{ config.transportation.bus or '' }}</textarea>
                </div>
                <div class="form-group">
                    <label>주차 정보</label>
                    <textarea name="parking_info">{{ config.transportation.parking or '' }}</textarea>
                </div>
            </div>

            <!-- 계좌 정보 -->
            <div class="section">
                <h2>💳 계좌 정보</h2>
                
                <h3 style="margin-top: 20px; margin-bottom: 15px;">신랑측 계좌</h3>
                <div id="groom-accounts">
                    {% for account in config.account_info.groom_accounts or [] %}
                    <div class="account-row">
                        <div class="form-row">
                            <div class="form-group">
                                <label>은행명</label>
                                <input type="text" name="groom_bank_{{ loop.index0 }}" value="{{ account.bank }}">
                            </div>
                            <div class="form-group">
                                <label>계좌번호</label>
                                <input type="text" name="groom_number_{{ loop.index0 }}" value="{{ account.number }}">
                            </div>
                            <div class="form-group">
                                <label>예금주</label>
                                <input type="text" name="groom_account_name_{{ loop.index0 }}" value="{{ account.name }}">
                            </div>
                            <div class="form-group">
                                <label>&nbsp;</label>
                                <button type="button" class="btn btn-danger" onclick="removeAccount(this)">삭제</button>
                            </div>
                        </div>
                    </div>
                    {% endfor %}
                </div>
                <input type="hidden" id="groom-account-count" name="groom_account_count" value="{{ (config.account_info.groom_accounts or [])|length }}">
                <button type="button" class="btn" onclick="addGroomAccount()">+ 신랑측 계좌 추가</button>
                
                <h3 style="margin-top: 30px; margin-bottom: 15px;">신부측 계좌</h3>
                <div id="bride-accounts">
                    {% for account in config.account_info.bride_accounts or [] %}
                    <div class="account-row">
                        <div class="form-row">
                            <div class="form-group">
                                <label>은행명</label>
                                <input type="text" name="bride_bank_{{ loop.index0 }}" value="{{ account.bank }}">
                            </div>
                            <div class="form-group">
                                <label>계좌번호</label>
                                <input type="text" name="bride_number_{{ loop.index0 }}" value="{{ account.number }}">
                            </div>
                            <div class="form-group">
                                <label>예금주</label>
                                <input type="text" name="bride_account_name_{{ loop.index0 }}" value="{{ account.name }}">
                            </div>
                            <div class="form-group">
                                <label>&nbsp;</label>
                                <button type="button" class="btn btn-danger" onclick="removeAccount(this)">삭제</button>
                            </div>
                        </div>
                    </div>
                    {% endfor %}
                </div>
                <input type="hidden" id="bride-account-count" name="bride_account_count" value="{{ (config.account_info.bride_accounts or [])|length }}">
                <button type="button" class="btn" onclick="addBrideAccount()">+ 신부측 계좌 추가</button>
            </div>

            <!-- 지도 관리 -->
            <div class="section">
                <h2>🗺️ 지도 관리</h2>
                
                <div class="form-group">
                    <label>현재 지도 이미지</label>
                    <div class="image-preview">
                        {% if config.map and config.map.image %}
                            {% set map_image_path = config.map.image %}
                            {% if map_image_path.startswith('http') %}
                                <img src="{{ map_image_path }}" class="current-image" alt="지도 이미지">
                            {% else %}
                                <img src="/{{ selected_slug }}/{{ map_image_path.lstrip('/') }}" class="current-image" alt="지도 이미지">
                            {% endif %}
                        {% else %}
                            <div class="no-image">현재 지도 이미지 없음</div>
                        {% endif %}
                    </div>
                    <input type="file" id="map-upload" style="display: none;" accept="image/*" onchange="uploadMapImage(this)">
                    <div class="image-upload" onclick="document.getElementById('map-upload').click()">
                        <p>📍 지도 이미지 업로드</p>
                        <small>클릭하여 지도 이미지 선택</small>
                    </div>
                </div>
                
                <div class="form-group">
                    <label>지도 링크 URL</label>
                    <input type="url" name="map_link" placeholder="https://naver.me/..." 
                           value="{{ config.map.link if config.map and config.map.link else '' }}">
                    <small>지도 이미지 클릭 시 이동할 URL을 입력하세요 (네이버 지도, 카카오맵 등)</small>
                </div>
            </div>

        </form>

            <!-- 배경음악 관리 -->
            <div class="section">
                <h2>🎵 배경음악 관리</h2>
            
            <div class="audio-section" style="max-width: 600px;">
                <div>
                    <label><strong>배경음악</strong></label>
                    <div class="audio-preview" style="margin: 10px 0; padding: 15px; border: 2px dashed #ddd; border-radius: 8px; text-align: center;">
                        {% if config.audio and config.audio.background_music %}
                        <div class="current-audio">
                            <audio controls style="width: 100%; margin-bottom: 10px;">
                                <source src="{{ config.audio.background_music }}" type="audio/mpeg">
                                현재 음악을 재생할 수 없습니다.
                            </audio>
                            <div style="font-size: 12px; color: #666;">
                                현재: {{ config.audio.background_music.split('/')[-1] }}
                            </div>
                        </div>
                        {% else %}
                        <div class="no-audio" style="color: #999; font-style: italic;">현재 배경음악 없음</div>
                        {% endif %}
                    </div>
                    <div class="audio-upload" onclick="document.getElementById('audio-upload').click()" 
                         style="padding: 20px; border: 2px dashed #007bff; border-radius: 8px; cursor: pointer; text-align: center; background: #f8f9fa; transition: all 0.2s;">
                        <p style="margin: 0 0 5px 0; color: #007bff; font-weight: bold;">🎵 클릭하여 배경음악 업로드</p>
                        <small style="color: #666;">지원 형식: MP3, WAV, OGG, M4A, AAC (최대 100MB)</small>
                    </div>
                    <input type="file" id="audio-upload" style="display: none;" accept="audio/*" onchange="uploadAudio(this)">
                    
                    <div style="margin-top: 20px; padding: 15px; background: #e3f2fd; border-radius: 8px;">
                        <div style="margin-bottom: 15px;">
                            <label style="display: flex; align-items: center; gap: 8px; cursor: pointer;">
                                <input type="checkbox" name="audio_autoplay" value="1" 
                                       {% if config.audio and config.audio.autoplay %}checked{% endif %}>
                                <span><strong>청첩장에서 자동 재생</strong></span>
                            </label>
                            <small style="color: #666; display: block; margin-top: 5px; margin-left: 24px;">
                                ⚠️ 일부 브라우저에서는 사용자 상호작용 후 재생됩니다
                            </small>
                        </div>
                        
                        <div style="margin-bottom: 15px;">
                            <label style="display: flex; align-items: center; gap: 8px; cursor: pointer;">
                                <input type="checkbox" name="audio_loop" value="1" 
                                       {% if config.audio and config.audio.loop %}checked{% endif %}>
                                <span><strong>음악 반복 재생</strong></span>
                            </label>
                        </div>
                        
                        <div>
                            <label style="display: block; margin-bottom: 8px; font-weight: bold;">음량 설정</label>
                            <div style="display: flex; align-items: center; gap: 10px;">
                                <input type="range" name="audio_volume" min="0" max="100" 
                                       value="{{ config.audio.volume if config.audio and config.audio.volume else 50 }}"
                                       style="flex: 1;" 
                                       oninput="this.nextElementSibling.textContent = this.value + '%'">
                                <span style="font-size: 14px; color: #666; min-width: 40px;">{{ config.audio.volume if config.audio and config.audio.volume else 50 }}%</span>
                            </div>
                        </div>
                    </div>
                    
                    <div style="margin-top: 20px; text-align: center;">
                        <button type="button" class="btn btn-primary" onclick="saveAudioSettings()">🎵 배경음악 설정 저장</button>
                    </div>
                </div>
            </div>
        </div>

        <!-- 이미지 관리 -->
        <div class="section">
            <h2>🖼️ 이미지 관리</h2>

            <div style="margin-bottom: 30px;">
                <label><strong>대표 썸네일 (SNS 공유 이미지)</strong></label>
                <p style="margin: 6px 0 12px 0; color: #666; font-size: 13px;">
                    카드 목록이나 SNS 미리보기에서 사용될 이미지를 설정하세요.
                </p>
                <div class="image-preview">
                    {% if config.meta and config.meta.thumbnail %}
                        {% set thumbnail_path = config.meta.thumbnail %}
                        {% if thumbnail_path.startswith('http') %}
                            <img src="{{ thumbnail_path }}" alt="대표 썸네일" class="current-image">
                        {% else %}
                            <img src="/{{ selected_slug }}/{{ thumbnail_path.lstrip('/') }}" alt="대표 썸네일" class="current-image">
                        {% endif %}
                    {% else %}
                        <div class="no-image">현재 썸네일 없음</div>
                    {% endif %}
                </div>
                <div class="image-upload" onclick="document.getElementById('thumbnail-upload').click()">
                    <p>📁 파일에서 대표 썸네일 업로드</p>
                    <small>권장 크기: 1200 x 630 (JPG, PNG)</small>
                </div>
                <input type="file" id="thumbnail-upload" style="display: none;" accept="image/*" onchange="uploadImage(this, 'thumbnail')">
                <div style="margin-top: 12px; display: flex; gap: 10px; flex-wrap: wrap;">
                    <button type="button" class="btn" style="background: #6c757d;" onclick="showUrlThumbnailModal('thumbnail')">🔗 URL로 설정</button>
                    <button type="button" class="btn btn-danger" onclick="removeThumbnail()" {% if not (config.meta and config.meta.thumbnail) %}disabled{% endif %}>🗑 썸네일 삭제</button>
                </div>
            </div>

            <h3 style="margin-top: 20px; margin-bottom: 10px;">메인 이미지들</h3>
            
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px;">
                <div>
                    <label><strong>메인 사진</strong></label>
                    <div class="image-preview">
                        {% if config.images.main_photo %}
                        <img src="{{ config.images.main_photo }}" alt="메인 사진" class="current-image">
                        {% else %}
                        <div class="no-image">현재 이미지 없음</div>
                        {% endif %}
                    </div>
                    <div class="image-upload" onclick="document.getElementById('main-upload').click()">
                        <p>클릭하여 메인 사진/영상 업로드</p>
                        <small>권장 크기: 627 x 853 (영상도 지원)</small>
                    </div>
                    <input type="file" id="main-upload" style="display: none;" accept="image/*,video/*" onchange="uploadImage(this, 'main')">
                </div>
                
                <div>
                    <label><strong>초대 사진</strong></label>
                    <div class="image-preview">
                        {% if config.images.invitation_photo %}
                            {% if config.images.invitation_photo_type == 'video' %}
                            <video src="{{ config.images.invitation_photo }}" class="current-image" controls muted loop style="max-width: 100%; height: auto;">
                                영상을 지원하지 않는 브라우저입니다.
                            </video>
                            {% else %}
                            <img src="{{ config.images.invitation_photo }}" alt="초대 사진" class="current-image">
                            {% endif %}
                        {% else %}
                        <div class="no-image">현재 이미지 없음</div>
                        {% endif %}
                    </div>
                    <div class="image-upload" onclick="document.getElementById('invitation-upload').click()">
                        <p>클릭하여 초대 사진/영상 업로드</p>
                    </div>
                    <input type="file" id="invitation-upload" style="display: none;" accept="image/*,video/*" onchange="uploadImage(this, 'invitation')">
                </div>
                
                <div>
                    <label><strong>포토부스 사진</strong></label>
                    <div class="image-preview">
                        {% if config.images.photobooth_photo %}
                            {% if config.images.photobooth_photo_type == 'video' %}
                            <video src="{{ config.images.photobooth_photo }}" class="current-image" controls muted loop style="max-width: 100%; height: auto;">
                                영상을 지원하지 않는 브라우저입니다.
                            </video>
                            {% else %}
                            <img src="{{ config.images.photobooth_photo }}" alt="포토부스 사진" class="current-image">
                            {% endif %}
                        {% else %}
                        <div class="no-image">현재 이미지 없음</div>
                        {% endif %}
                    </div>
                    <div class="image-upload" onclick="document.getElementById('photobooth-upload').click()">
                        <p>클릭하여 포토부스 사진/영상 업로드</p>
                    </div>
                    <input type="file" id="photobooth-upload" style="display: none;" accept="image/*,video/*" onchange="uploadImage(this, 'photobooth')">
                </div>
                
                <div>
                    <label><strong>마무리 사진</strong></label>
                    <div class="image-preview">
                        {% if config.images.outro_photo %}
                            {% if config.images.outro_photo_type == 'video' %}
                            <video src="{{ config.images.outro_photo }}" class="current-image" controls muted loop style="max-width: 100%; height: auto;">
                                영상을 지원하지 않는 브라우저입니다.
                            </video>
                            {% else %}
                            <img src="{{ config.images.outro_photo }}" alt="마무리 사진" class="current-image">
                            {% endif %}
                        {% else %}
                        <div class="no-image">현재 이미지 없음</div>
                        {% endif %}
                    </div>
                    <div class="image-upload" onclick="document.getElementById('outro-upload').click()">
                        <p>클릭하여 마무리 사진/영상 업로드</p>
                    </div>
                    <input type="file" id="outro-upload" style="display: none;" accept="image/*,video/*" onchange="uploadImage(this, 'outro')">
                </div>
            </div>

            <h3 style="margin-top: 30px; margin-bottom: 10px;">갤러리 이미지들</h3>
            <div style="background: #e3f2fd; padding: 15px; border-radius: 8px; margin-bottom: 15px; border-left: 4px solid #2196f3;">
                <h4 style="margin: 0 0 8px 0; color: #1976d2;">📖 사용 방법</h4>
                <ul style="margin: 0; padding-left: 20px; color: #555;">
                    <li><strong>파일 업로드:</strong> 📁 버튼으로 컴퓨터에서 이미지/영상 선택</li>
                    <li><strong>URL 추가:</strong> 🔗 버튼으로 웹상의 이미지 URL 입력 (인스타그램, 구글 포토 등)</li>
                    <li><strong>순서 변경:</strong> 이미지를 끌어서 원하는 위치에 배치</li>
                    <li><strong>크기 조정:</strong> 이미지에 마우스를 올리고 하단의 "가로/세로" 버튼 클릭</li>
                    <li><strong>삭제:</strong> 이미지에 마우스를 올리고 우상단 ❌ 버튼 클릭</li>
                    <li><strong>저장:</strong> 변경 후 반드시 "갤러리 순서 및 크기 저장" 버튼 클릭</li>
                </ul>
            </div>
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 15px;">
                <div class="image-upload" onclick="document.getElementById('gallery-upload').click()">
                    <p>📁 파일에서 업로드</p>
                    <small>이미지/영상 파일 선택</small>
                </div>
                <div class="image-upload" onclick="showUrlThumbnailModal('gallery')">
                    <p>🔗 URL로 이미지 추가</p>
                    <small>웹 이미지 URL 입력</small>
                </div>
            </div>
            <input type="file" id="gallery-upload" style="display: none;" accept="image/*,video/*" multiple onchange="uploadImage(this, 'gallery')">
            
            <div class="gallery-grid" id="gallery-grid">
                {% for item in config.gallery_images or [] %}
                {% set current_size = item.size if item is mapping else 'small' %}
                {% set item_path = item.path if item is mapping else item %}
                {% set item_type = item.type if item is mapping else 'image' %}
                <div class="gallery-item size-{{ current_size }}" draggable="true" data-index="{{ loop.index0 }}" data-size="{{ current_size }}" data-type="{{ item_type }}">
                    {% if item_type == 'video' %}
                    <video src="{{ item_path }}" muted loop class="gallery-video">
                        <source src="{{ item_path }}" type="video/mp4">
                        영상을 지원하지 않는 브라우저입니다.
                    </video>
                    <div class="video-indicator">🎬</div>
                    {% elif item_type == 'url_image' %}
                    <img src="{{ item_path }}" alt="URL 이미지" crossorigin="anonymous">
                    <div class="url-indicator">🔗</div>
                    {% else %}
                    <img src="{{ item_path }}" alt="갤러리 이미지">
                    {% endif %}
                    <div class="gallery-controls">
                        <button class="control-btn" onclick="deleteGalleryImage({{ loop.index0 }})" title="삭제">×</button>
                    </div>
                    <div class="size-controls">
                        <button class="size-btn {{ 'active' if current_size == 'small' else '' }}" onclick="changeImageSize({{ loop.index0 }}, 'small')">가로</button>
                        <button class="size-btn {{ 'active' if current_size == 'tall' else '' }}" onclick="changeImageSize({{ loop.index0 }}, 'tall')">세로</button>
                    </div>
                </div>
                {% endfor %}
            </div>
            
            {% if config.gallery_images and config.gallery_images|length > 0 %}
            <div style="margin-top: 15px; text-align: center;">
                <button type="button" class="btn btn-success" onclick="saveGalleryOrder()">📋 갤러리 순서 및 크기 저장</button>
            </div>
            {% endif %}
        </div>
    </div>

    <!-- URL 썸네일 모달 -->
    <div id="url-thumbnail-modal" style="display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.5); z-index: 10000;">
        <div style="position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); background: white; padding: 30px; border-radius: 8px; width: 90%; max-width: 500px;">
            <h3 id="url-thumbnail-modal-title" style="margin: 0 0 20px 0; color: #333;">🔗 URL로 썸네일 추가</h3>
            
            <div style="margin-bottom: 20px;">
                <label style="display: block; margin-bottom: 5px; font-weight: bold; color: #555;">이미지 URL</label>
                <input type="url" id="thumbnail-url" placeholder="https://example.com/image.jpg" style="width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 4px; font-size: 14px;">
                <small id="url-thumbnail-helper" style="color: #666; margin-top: 5px; display: block;">직접 이미지 링크를 입력하세요 (jpg, png, gif, webp 등)</small>
            </div>
            
            <div style="margin-bottom: 20px;">
                <label style="display: block; margin-bottom: 5px; font-weight: bold; color: #555;">미리보기</label>
                <div id="url-preview" style="border: 2px dashed #ddd; padding: 20px; text-align: center; border-radius: 4px; min-height: 100px; display: flex; align-items: center; justify-content: center; color: #666;">
                    URL을 입력하면 미리보기가 표시됩니다
                </div>
            </div>
            
            <div style="text-align: right;">
                <button type="button" onclick="closeUrlThumbnailModal()" style="padding: 10px 20px; background: #6c757d; color: white; border: none; border-radius: 4px; cursor: pointer; margin-right: 10px;">취소</button>
                <button type="button" id="url-thumbnail-submit" onclick="addUrlThumbnail()" style="padding: 10px 20px; background: #28a745; color: white; border: none; border-radius: 4px; cursor: pointer;">추가</button>
            </div>
        </div>
    </div>

    <script>
        const invitationState = {
            list: {{ invitations | tojson }},
            currentSlug: '{{ selected_slug or '' }}',
            defaultSlug: '{{ default_slug or '' }}'
        };
        window.currentSlug = invitationState.currentSlug || '';
        if (!window.currentSlug && invitationState.list && invitationState.list.length) {
            window.currentSlug = invitationState.list[0].slug;
        }
        window.defaultSlug = invitationState.defaultSlug;

        function appendSlug(formData) {
            if (window.currentSlug) {
                formData.append('invitation_slug', window.currentSlug);
            }
        }

        function withSlug(payload) {
            const base = payload && typeof payload === 'object' ? payload : {};
            return window.currentSlug ? { ...base, slug: window.currentSlug } : { ...base };
        }

        let urlThumbnailMode = 'gallery';

        document.addEventListener('DOMContentLoaded', function() {
            const invitationSelect = document.getElementById('invitation-select');
            const createBtn = document.getElementById('create-invitation-btn');
            const duplicateBtn = document.getElementById('duplicate-invitation-btn');
            const renameBtn = document.getElementById('rename-invitation-btn');
            const renameSlugBtn = document.getElementById('rename-slug-btn');
            const deleteBtn = document.getElementById('delete-invitation-btn');
            const setDefaultBtn = document.getElementById('set-default-btn');
            const previewLink = document.getElementById('preview-link');
            const adminForm = document.getElementById('admin-form');
            const floatingSaveBtn = document.getElementById('floating-save-btn');

            if (floatingSaveBtn && adminForm) {
                const defaultLabel = floatingSaveBtn.innerHTML;

                const setSavingState = (isSaving) => {
                    floatingSaveBtn.disabled = isSaving;
                    if (isSaving) {
                        floatingSaveBtn.innerHTML = '💾 저장 중...';
                    } else {
                        floatingSaveBtn.innerHTML = defaultLabel;
                    }
                };

                floatingSaveBtn.addEventListener('click', () => {
                    if (floatingSaveBtn.disabled) {
                        return;
                    }
                    setSavingState(true);
                    adminForm.requestSubmit();
                });

                adminForm.addEventListener('submit', () => {
                    setSavingState(true);
                });

                window.addEventListener('pageshow', () => {
                    setSavingState(false);
                });
            }

            if (previewLink && window.currentSlug) {
                previewLink.href = `/${window.currentSlug}`;
            }

            if (invitationSelect) {
                invitationSelect.addEventListener('change', function() {
                    if (this.value && this.value !== window.currentSlug) {
                        window.location.href = `/admin?slug=${encodeURIComponent(this.value)}`;
                    }
                });
            }

            if (createBtn) {
                createBtn.addEventListener('click', function() {
                    const name = prompt('새 청첩장의 이름을 입력하세요:', '');
                    if (!name) {
                        return;
                    }
                    const trimmedName = name.trim();
                    if (!trimmedName) {
                        return;
                    }

                    fetch('/admin/invitations', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ name: trimmedName })
                    })
                    .then(response => response.json())
                    .then(data => {
                        if (data.success) {
                            window.location.href = `/admin?slug=${encodeURIComponent(data.invitation.slug)}`;
                        } else {
                            alert(data.message || '청첩장 생성에 실패했습니다.');
                        }
                    })
                    .catch(error => {
                        console.error('청첩장 생성 오류:', error);
                        alert('청첩장 생성 중 오류가 발생했습니다.');
                    });
                });
            }

            if (renameBtn) {
                renameBtn.addEventListener('click', function() {
                    if (!window.currentSlug) {
                        return;
                    }
                    const currentOption = invitationSelect ? invitationSelect.options[invitationSelect.selectedIndex] : null;
                    const currentName = currentOption ? currentOption.text.replace(' (기본)', '') : '';
                    const name = prompt('새 청첩장 이름을 입력하세요:', currentName);
                    if (!name) {
                        return;
                    }
                    const trimmedName = name.trim();
                    if (!trimmedName) {
                        return;
                    }

                    fetch(`/admin/invitations/${encodeURIComponent(window.currentSlug)}`, {
                        method: 'PATCH',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ name: trimmedName })
                    })
                    .then(response => response.json())
                    .then(data => {
                        if (data.success) {
                            window.location.href = `/admin?slug=${encodeURIComponent(window.currentSlug)}`;
                        } else {
                            alert(data.message || '이름 변경에 실패했습니다.');
                        }
                    })
                    .catch(error => {
                        console.error('청첩장 이름 변경 오류:', error);
                        alert('이름 변경 중 오류가 발생했습니다.');
                    });
                });
            }

            if (renameSlugBtn) {
                renameSlugBtn.addEventListener('click', function() {
                    if (!window.currentSlug) {
                        alert('변경할 청첩장을 찾을 수 없습니다.');
                        return;
                    }

                    const newSlug = prompt('새 슬러그(폴더명)를 입력하세요:\\n영문, 숫자, 하이픈만 사용됩니다.', window.currentSlug);
                    if (newSlug === null) {
                        return;
                    }

                    const trimmedSlug = newSlug.trim();
                    if (!trimmedSlug) {
                        alert('유효한 슬러그를 입력해주세요.');
                        return;
                    }

                    fetch(`/admin/invitations/${encodeURIComponent(window.currentSlug)}`, {
                        method: 'PATCH',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ new_slug: trimmedSlug })
                    })
                    .then(response => response.json())
                    .then(data => {
                        if (data.success) {
                            const nextSlug = (data.updates && data.updates.slug) || window.currentSlug;
                            window.location.href = `/admin?slug=${encodeURIComponent(nextSlug)}`;
                        } else {
                            alert(data.message || '슬러그 변경에 실패했습니다.');
                        }
                    })
                    .catch(error => {
                        console.error('슬러그 변경 오류:', error);
                        alert('슬러그 변경 중 오류가 발생했습니다.');
                    });
                });
            }

            if (duplicateBtn) {
                duplicateBtn.addEventListener('click', function() {
                    if (!window.currentSlug) {
                        alert('복제할 청첩장을 찾을 수 없습니다.');
                        return;
                    }
                    const name = prompt('복제된 청첩장의 이름을 입력하세요:', '');
                    if (!name) {
                        return;
                    }
                    const trimmedName = name.trim();
                    if (!trimmedName) {
                        return;
                    }

                    fetch('/admin/invitations', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ name: trimmedName, copy_from: window.currentSlug })
                    })
                    .then(response => response.json())
                    .then(data => {
                        if (data.success) {
                            window.location.href = `/admin?slug=${encodeURIComponent(data.invitation.slug)}`;
                        } else {
                            alert(data.message || '청첩장 복제에 실패했습니다.');
                        }
                    })
                    .catch(error => {
                        console.error('청첩장 복제 오류:', error);
                        alert('청첩장 복제 중 오류가 발생했습니다.');
                    });
                });
            }

            if (setDefaultBtn) {
                setDefaultBtn.addEventListener('click', function() {
                    if (!window.currentSlug) {
                        return;
                    }
                    fetch(`/admin/invitations/${encodeURIComponent(window.currentSlug)}/set-default`, { method: 'POST' })
                        .then(response => response.json())
                        .then(data => {
                            if (data.success) {
                                window.location.href = `/admin?slug=${encodeURIComponent(window.currentSlug)}`;
                            } else {
                                alert(data.message || '기본 설정에 실패했습니다.');
                            }
                        })
                        .catch(error => {
                            console.error('기본 설정 오류:', error);
                            alert('기본 설정 중 오류가 발생했습니다.');
                        });
                });
            }

            if (deleteBtn) {
                deleteBtn.addEventListener('click', function() {
                    if (!window.currentSlug) {
                        return;
                    }
                    if (!confirm('정말로 이 청첩장을 삭제하시겠습니까? 되돌릴 수 없습니다.')) {
                        return;
                    }
                    fetch(`/admin/invitations/${encodeURIComponent(window.currentSlug)}`, { method: 'DELETE' })
                        .then(response => response.json())
                        .then(data => {
                            if (data.success) {
                                const nextSlug = data.default_slug || (data.invitations && data.invitations.length ? data.invitations[0].slug : '');
                                if (nextSlug) {
                                    window.location.href = `/admin?slug=${encodeURIComponent(nextSlug)}`;
                                } else {
                                    window.location.href = '/admin';
                                }
                            } else {
                                alert(data.message || '삭제에 실패했습니다.');
                            }
                        })
                        .catch(error => {
                            console.error('청첩장 삭제 오류:', error);
                            alert('청첩장 삭제 중 오류가 발생했습니다.');
                        });
                });
            }
        });

        function uploadImage(input, type) {
            const files = input.files;
            const isThumbnail = type === 'thumbnail';
            if (files.length === 0) {
                console.log('파일이 선택되지 않았습니다.');
                return;
            }

            if (isThumbnail && files.length > 1) {
                input.value = '';
                alert('썸네일은 하나의 이미지 파일만 업로드할 수 있습니다.');
                return;
            }

            console.log(`업로드 시작: ${files.length}개 파일, 타입: ${type}`);
            
            // 업로드 진행 표시
            showUploadProgress();
            
            if (type === 'gallery') {
                // 갤러리는 여러 파일을 순차적으로 업로드 (모바일 안정성 향상)
                uploadGalleryFiles(Array.from(files), 0);
            } else {
                // 단일 파일 업로드
                uploadSingleFile(files[0], type);
            }
            
            // 파일 입력 초기화 (모바일에서 같은 파일 재선택 가능)
            input.value = '';
        }
        
        function uploadGalleryFiles(files, index) {
            if (index >= files.length) {
                hideUploadProgress();
                alert(`${files.length}개 파일이 업로드되었습니다!`);
                setTimeout(() => location.reload(), 500);
                return;
            }
            
            const file = files[index];
            console.log(`갤러리 파일 업로드 ${index + 1}/${files.length}: ${file.name} (${file.size} bytes)`);
            
            // 파일 크기 검증 (100MB 제한)
            if (file.size > 100 * 1024 * 1024) {
                alert(`파일이 너무 큽니다: ${file.name} (최대 100MB)`);
                uploadGalleryFiles(files, index + 1);
                return;
            }
            
            const formData = new FormData();
            formData.append('file', file);
            formData.append('image_type', 'gallery');
            appendSlug(formData);
            
            fetch('/admin/upload_image', {
                method: 'POST',
                body: formData
            })
            .then(response => {
                console.log(`응답 상태: ${response.status}`);
                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                }
                return response.json();
            })
            .then(data => {
                console.log(`업로드 응답:`, data);
                if (data.success) {
                    updateUploadProgress(index + 1, files.length);
                    // 다음 파일 업로드 (모바일에서 안정성을 위해 지연)
                    setTimeout(() => uploadGalleryFiles(files, index + 1), 200);
                } else {
                    hideUploadProgress();
                    alert(`업로드 실패 (${index + 1}/${files.length}): ${data.message}`);
                }
            })
            .catch(error => {
                console.error(`업로드 오류 (${index + 1}/${files.length}):`, error);
                hideUploadProgress();
                alert(`업로드 중 오류가 발생했습니다: ${error.message || '네트워크 오류'}`);
            });
        }
        
        function uploadSingleFile(file, type) {
            console.log(`단일 파일 업로드: ${file.name} (${file.size} bytes), 타입: ${type}`);
            const isThumbnail = type === 'thumbnail';

            if (isThumbnail && file.type && !file.type.startsWith('image/')) {
                hideUploadProgress();
                alert('썸네일은 이미지 파일만 업로드할 수 있습니다.');
                return;
            }
            
            // 파일 크기 검증 (100MB 제한)
            if (file.size > 100 * 1024 * 1024) {
                hideUploadProgress();
                alert(`파일이 너무 큽니다: ${file.name} (최대 100MB)`);
                return;
            }
            
            const formData = new FormData();
            formData.append('file', file);
            formData.append('image_type', type);
            appendSlug(formData);
            
            fetch('/admin/upload_image', {
                method: 'POST',
                body: formData
            })
            .then(response => {
                console.log(`응답 상태: ${response.status}`);
                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                }
                return response.json();
            })
            .then(data => {
                console.log(`업로드 응답:`, data);
                hideUploadProgress();
                if (data.success) {
                    const message = isThumbnail ? '대표 썸네일이 업로드되었습니다!' : '이미지가 업로드되었습니다!';
                    alert(message);
                    setTimeout(() => location.reload(), 500);
                } else {
                    alert(`업로드 실패: ${data.message}`);
                }
            })
            .catch(error => {
                console.error('업로드 오류:', error);
                hideUploadProgress();
                alert(`업로드 중 오류가 발생했습니다: ${error.message || '네트워크 오류'}`);
            });
        }
        
        function showUploadProgress() {
            // 기존 프로그레스 제거
            hideUploadProgress();
            
            const progress = document.createElement('div');
            progress.id = 'upload-progress';
            progress.style.cssText = `
                position: fixed;
                top: 50%;
                left: 50%;
                transform: translate(-50%, -50%);
                background: white;
                padding: 20px;
                border-radius: 8px;
                box-shadow: 0 4px 12px rgba(0,0,0,0.3);
                z-index: 10001;
                text-align: center;
                min-width: 200px;
                max-width: 90vw;
            `;
            progress.innerHTML = `
                <div style="color: #007bff; font-size: 16px; margin-bottom: 10px;">📤 업로드 중...</div>
                <div id="progress-text" style="color: #666; font-size: 14px;">파일을 업로드하고 있습니다</div>
                <div style="margin-top: 10px; color: #999; font-size: 12px;">잠시만 기다려주세요</div>
            `;
            
            // 배경 오버레이
            const overlay = document.createElement('div');
            overlay.id = 'upload-overlay';
            overlay.style.cssText = `
                position: fixed;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                background: rgba(0,0,0,0.5);
                z-index: 10000;
            `;
            
            document.body.appendChild(overlay);
            document.body.appendChild(progress);
        }
        
        function updateUploadProgress(current, total) {
            const progressText = document.getElementById('progress-text');
            if (progressText) {
                progressText.textContent = `${current}/${total} 파일 업로드 완료`;
            }
        }
        
        function hideUploadProgress() {
            const progress = document.getElementById('upload-progress');
            const overlay = document.getElementById('upload-overlay');
            if (progress) progress.remove();
            if (overlay) overlay.remove();
        }

        function deleteGalleryImage(index) {
            if (confirm('이 이미지를 삭제하시겠습니까?')) {
                const slugParam = window.currentSlug ? `?slug=${encodeURIComponent(window.currentSlug)}` : '';
                window.location.href = '/admin/delete_gallery/' + index + slugParam;
            }
        }
        
        // 계좌 관리 함수들
        function addGroomAccount() {
            const container = document.getElementById('groom-accounts');
            const countInput = document.getElementById('groom-account-count');
            const currentCount = parseInt(countInput.value);
            
            const accountRow = document.createElement('div');
            accountRow.className = 'account-row';
            accountRow.innerHTML = `
                <div class="form-row">
                    <div class="form-group">
                        <label>은행명</label>
                        <input type="text" name="groom_bank_${currentCount}" placeholder="예: 국민은행">
                    </div>
                    <div class="form-group">
                        <label>계좌번호</label>
                        <input type="text" name="groom_number_${currentCount}" placeholder="계좌번호를 입력하세요">
                    </div>
                    <div class="form-group">
                        <label>예금주</label>
                        <input type="text" name="groom_account_name_${currentCount}" placeholder="예금주명을 입력하세요">
                    </div>
                    <div class="form-group">
                        <label>&nbsp;</label>
                        <button type="button" class="btn btn-danger" onclick="removeAccount(this)">삭제</button>
                    </div>
                </div>
            `;
            
            container.appendChild(accountRow);
            countInput.value = currentCount + 1;
        }
        
        function addBrideAccount() {
            const container = document.getElementById('bride-accounts');
            const countInput = document.getElementById('bride-account-count');
            const currentCount = parseInt(countInput.value);
            
            const accountRow = document.createElement('div');
            accountRow.className = 'account-row';
            accountRow.innerHTML = `
                <div class="form-row">
                    <div class="form-group">
                        <label>은행명</label>
                        <input type="text" name="bride_bank_${currentCount}" placeholder="예: 신한은행">
                    </div>
                    <div class="form-group">
                        <label>계좌번호</label>
                        <input type="text" name="bride_number_${currentCount}" placeholder="계좌번호를 입력하세요">
                    </div>
                    <div class="form-group">
                        <label>예금주</label>
                        <input type="text" name="bride_account_name_${currentCount}" placeholder="예금주명을 입력하세요">
                    </div>
                    <div class="form-group">
                        <label>&nbsp;</label>
                        <button type="button" class="btn btn-danger" onclick="removeAccount(this)">삭제</button>
                    </div>
                </div>
            `;
            
            container.appendChild(accountRow);
            countInput.value = currentCount + 1;
        }
        
        function removeAccount(button) {
            if (confirm('이 계좌를 삭제하시겠습니까?')) {
                const accountRow = button.closest('.account-row');
                const container = accountRow.parentNode;
                const isGroom = container.id === 'groom-accounts';
                const countInput = document.getElementById(isGroom ? 'groom-account-count' : 'bride-account-count');
                
                accountRow.remove();
                
                // 인덱스 재정렬
                const rows = container.querySelectorAll('.account-row');
                rows.forEach((row, index) => {
                    const prefix = isGroom ? 'groom' : 'bride';
                    const inputs = row.querySelectorAll('input[type="text"]');
                    inputs[0].name = `${prefix}_bank_${index}`;
                    inputs[1].name = `${prefix}_number_${index}`;
                    inputs[2].name = `${prefix}_account_name_${index}`;
                });
                
                countInput.value = rows.length;
            }
        }
        
        // 지도 이미지 업로드 함수
        function uploadMapImage(input) {
            const file = input.files[0];
            if (!file) {
                console.log('지도 이미지가 선택되지 않았습니다.');
                return;
            }
            
            // 파일 크기 검증 (10MB 제한)
            if (file.size > 10 * 1024 * 1024) {
                alert('파일 크기가 너무 큽니다. 10MB 이하의 파일을 선택해주세요.');
                input.value = '';
                return;
            }
            
            console.log('지도 이미지 업로드 시작:', file.name);
            showUploadProgress();
            
            const formData = new FormData();
            formData.append('file', file);
            formData.append('type', 'map');
            appendSlug(formData);

            fetch('/admin/upload_map', {
                method: 'POST',
                body: formData
            })
            .then(response => {
                console.log(`지도 업로드 응답 상태: ${response.status}`);
                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                }
                return response.json();
            })
            .then(data => {
                console.log('지도 업로드 응답:', data);
                hideUploadProgress();
                if (data.success) {
                    // 이미지 미리보기 업데이트
                    const preview = document.querySelector('.image-preview');
                    if (preview) {
                        preview.innerHTML = `<img src="${data.file_path}" class="current-image" alt="지도 이미지">`;
                    }
                    alert('지도 이미지가 업로드되었습니다!');
                } else {
                    alert(`업로드 실패: ${data.message}`);
                }
            })
            .catch(error => {
                console.error('지도 업로드 오류:', error);
                hideUploadProgress();
                alert(`업로드 중 오류가 발생했습니다: ${error.message || '네트워크 오류'}`);
            })
            .finally(() => {
                input.value = '';
            });
        }
        
        // 배경음악 설정 저장 함수
        function saveAudioSettings() {
            const autoplay = document.querySelector('input[name="audio_autoplay"]').checked;
            const loop = document.querySelector('input[name="audio_loop"]').checked;
            const volume = document.querySelector('input[name="audio_volume"]').value;
            
            console.log('배경음악 설정 저장:', { autoplay, loop, volume });
            
            // 업로드 진행 표시
            showUploadProgress();
            
            const formData = new FormData();
            formData.append('audio_autoplay', autoplay ? '1' : '');
            formData.append('audio_loop', loop ? '1' : '');
            formData.append('audio_volume', volume);
            appendSlug(formData);

            fetch('/admin/save_audio_settings', {
                method: 'POST',
                body: formData
            })
            .then(response => {
                console.log(`오디오 설정 저장 응답 상태: ${response.status}`);
                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                }
                return response.json();
            })
            .then(data => {
                console.log('오디오 설정 저장 응답:', data);
                hideUploadProgress();
                if (data.success) {
                    alert('배경음악 설정이 저장되었습니다!');
                } else {
                    alert(`저장 실패: ${data.message}`);
                }
            })
            .catch(error => {
                console.error('오디오 설정 저장 오류:', error);
                hideUploadProgress();
                alert(`설정 저장 중 오류가 발생했습니다: ${error.message || '네트워크 오류'}`);
            });
        }
        
        // 오디오 업로드 함수
        function uploadAudio(input) {
            const file = input.files[0];
            if (!file) {
                console.log('오디오 파일이 선택되지 않았습니다.');
                return;
            }

            console.log(`오디오 업로드 시작: ${file.name} (${file.size} bytes)`);
            
            // 파일 크기 검증 (100MB 제한)
            if (file.size > 100 * 1024 * 1024) {
                alert(`파일이 너무 큽니다: ${file.name} (최대 100MB)`);
                return;
            }
            
            // 오디오 파일 확장자 검증
            const allowedAudioExts = ['mp3', 'wav', 'ogg', 'm4a', 'aac'];
            const fileExt = file.name.split('.').pop().toLowerCase();
            if (!allowedAudioExts.includes(fileExt)) {
                alert(`지원하지 않는 오디오 형식입니다. 지원 형식: ${allowedAudioExts.join(', ')}`);
                return;
            }
            
            // 업로드 진행 표시
            showUploadProgress();
            
            const formData = new FormData();
            formData.append('file', file);
            formData.append('audio_type', 'background');
            appendSlug(formData);

            fetch('/admin/upload_audio', {
                method: 'POST',
                body: formData
            })
            .then(response => {
                console.log(`오디오 업로드 응답 상태: ${response.status}`);
                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                }
                return response.json();
            })
            .then(data => {
                console.log('오디오 업로드 응답:', data);
                hideUploadProgress();
                if (data.success) {
                    alert('배경음악이 업로드되었습니다!');
                    setTimeout(() => location.reload(), 500);
                } else {
                    alert(`업로드 실패: ${data.message}`);
                }
            })
            .catch(error => {
                console.error('오디오 업로드 오류:', error);
                hideUploadProgress();
                alert(`업로드 중 오류가 발생했습니다: ${error.message || '네트워크 오류'}`);
            });
            
            // 파일 입력 초기화
            input.value = '';
        }
        
        // URL 썸네일 모달 관련 함수들
        function showUrlThumbnailModal(mode) {
            urlThumbnailMode = mode || 'gallery';
            const modal = document.getElementById('url-thumbnail-modal');
            if (!modal) {
                return;
            }

            modal.style.display = 'block';
            const urlInput = document.getElementById('thumbnail-url');
            const preview = document.getElementById('url-preview');
            const titleEl = document.getElementById('url-thumbnail-modal-title');
            const helperEl = document.getElementById('url-thumbnail-helper');
            const submitBtn = document.getElementById('url-thumbnail-submit');

            if (urlInput) {
                urlInput.value = '';
            }
            if (preview) {
                preview.innerHTML = 'URL을 입력하면 미리보기가 표시됩니다';
            }

            if (urlThumbnailMode === 'thumbnail') {
                if (titleEl) titleEl.textContent = '🔗 URL로 대표 썸네일 설정';
                if (helperEl) helperEl.textContent = 'SNS 공유 등에서 사용할 대표 이미지 URL을 입력하세요.';
                if (submitBtn) submitBtn.textContent = '설정';
            } else {
                if (titleEl) titleEl.textContent = '🔗 URL로 썸네일 추가';
                if (helperEl) helperEl.textContent = '직접 이미지 링크를 입력하세요 (jpg, png, gif, webp 등)';
                if (submitBtn) submitBtn.textContent = '추가';
            }
        }

        function closeUrlThumbnailModal() {
            const modal = document.getElementById('url-thumbnail-modal');
            if (modal) {
                modal.style.display = 'none';
            }
            urlThumbnailMode = 'gallery';
        }
        
        // URL 입력 시 실시간 미리보기
        document.addEventListener('DOMContentLoaded', function() {
            const urlInput = document.getElementById('thumbnail-url');
            const preview = document.getElementById('url-preview');
            let previewTimeout;
            
            if (urlInput) {
                urlInput.addEventListener('input', function() {
                    clearTimeout(previewTimeout);
                    const url = this.value.trim();
                    
                    if (!url) {
                        preview.innerHTML = 'URL을 입력하면 미리보기가 표시됩니다';
                        return;
                    }
                    
                    // URL 형식 간단 검증
                    if (!isValidImageUrl(url)) {
                        preview.innerHTML = '<span style="color: #dc3545;">⚠️ 올바른 이미지 URL을 입력해주세요</span>';
                        return;
                    }
                    
                    preview.innerHTML = '<span style="color: #007bff;">🔄 미리보기 로딩중...</span>';
                    
                    // 0.5초 후에 미리보기 로드 (사용자가 타이핑을 멈출 때까지 기다림)
                    previewTimeout = setTimeout(() => {
                        loadUrlPreview(url);
                    }, 500);
                });
            }
        });
        
        function isValidImageUrl(url) {
            if (!url) {
                return false;
            }

            if (url.startsWith('/') || url.startsWith('assets/')) {
                return /\.(jpg|jpeg|png|gif|webp|svg|bmp)$/i.test(url.toLowerCase());
            }

            try {
                const urlObj = new URL(url);
                const pathname = urlObj.pathname.toLowerCase();
                return /\.(jpg|jpeg|png|gif|webp|svg|bmp)$/i.test(pathname) || 
                       url.includes('imgur.com') || 
                       url.includes('images') ||
                       url.includes('photo') ||
                       url.includes('pic');
            } catch {
                return false;
            }
        }
        
        function loadUrlPreview(url) {
            const preview = document.getElementById('url-preview');
            if (!preview) {
                return;
            }

            let previewUrl = url;
            if (url.startsWith('assets/')) {
                const prefix = window.currentSlug ? `/${window.currentSlug}/` : '/';
                previewUrl = `${prefix}${url.replace(/^\/+/, '')}`;
            }

            const img = new Image();

            img.onload = function() {
                preview.innerHTML = `<img src="${previewUrl}" style="max-width: 100%; max-height: 200px; border-radius: 4px;" alt="미리보기">`;
            };

            img.onerror = function() {
                preview.innerHTML = '<span style="color: #dc3545;">❌ 이미지를 불러올 수 없습니다. URL을 확인해주세요.</span>';
            };

            img.src = previewUrl;
        }
        
        function addUrlThumbnail() {
            const url = document.getElementById('thumbnail-url').value.trim();
            
            if (!url) {
                alert('URL을 입력해주세요.');
                return;
            }
            
            if (!isValidImageUrl(url)) {
                alert('올바른 이미지 URL을 입력해주세요.');
                return;
            }
            
            let endpoint = '/admin/add_url_thumbnail';
            let payload = { url: url, size: 'small', type: 'url_image' };
            let successMessage = 'URL 썸네일이 추가되었습니다!';

            if (urlThumbnailMode === 'thumbnail') {
                endpoint = '/admin/set_thumbnail_url';
                payload = { url: url };
                successMessage = '대표 썸네일이 설정되었습니다!';
            }

            // 서버에 URL 데이터 전송
            fetch(endpoint, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(withSlug(payload))
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    alert(successMessage);
                    closeUrlThumbnailModal();
                    location.reload();
                } else {
                    alert('추가 실패: ' + data.message);
                }
            })
            .catch(error => {
                console.error('URL 썸네일 추가 오류:', error);
                alert('추가 중 오류가 발생했습니다.');
            });
        }

        function removeThumbnail() {
            if (!window.currentSlug) {
                alert('삭제할 청첩장을 먼저 선택해주세요.');
                return;
            }

            if (!confirm('대표 썸네일을 삭제하시겠습니까?')) {
                return;
            }

            fetch('/admin/thumbnail', {
                method: 'DELETE',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(withSlug({}))
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    alert('대표 썸네일이 삭제되었습니다.');
                    location.reload();
                } else {
                    alert('삭제 실패: ' + data.message);
                }
            })
            .catch(error => {
                console.error('썸네일 삭제 오류:', error);
                alert('삭제 중 오류가 발생했습니다.');
            });
        }
        
        // 갤러리 드래그 앤 드롭 기능
        let draggedItem = null;
        
        document.addEventListener('DOMContentLoaded', function() {
            initGalleryDragDrop();
        });
        
        function initGalleryDragDrop() {
            const galleryGrid = document.getElementById('gallery-grid');
            if (!galleryGrid) return;
            
            const items = galleryGrid.querySelectorAll('.gallery-item');
            
            items.forEach(item => {
                item.addEventListener('dragstart', handleDragStart);
                item.addEventListener('dragover', handleDragOver);
                item.addEventListener('drop', handleDrop);
                item.addEventListener('dragend', handleDragEnd);
                item.addEventListener('dragenter', handleDragEnter);
                item.addEventListener('dragleave', handleDragLeave);
            });
        }
        
        function handleDragStart(e) {
            draggedItem = this;
            this.classList.add('dragging');
            e.dataTransfer.effectAllowed = 'move';
            e.dataTransfer.setData('text/html', this.outerHTML);
        }
        
        function handleDragOver(e) {
            if (e.preventDefault) {
                e.preventDefault();
            }
            e.dataTransfer.dropEffect = 'move';
            return false;
        }
        
        function handleDragEnter(e) {
            if (this !== draggedItem) {
                this.classList.add('drag-over');
            }
        }
        
        function handleDragLeave(e) {
            this.classList.remove('drag-over');
        }
        
        function handleDrop(e) {
            if (e.stopPropagation) {
                e.stopPropagation();
            }
            
            if (draggedItem !== this) {
                const galleryGrid = document.getElementById('gallery-grid');
                const allItems = Array.from(galleryGrid.children);
                const draggedIndex = allItems.indexOf(draggedItem);
                const targetIndex = allItems.indexOf(this);
                
                if (draggedIndex < targetIndex) {
                    galleryGrid.insertBefore(draggedItem, this.nextSibling);
                } else {
                    galleryGrid.insertBefore(draggedItem, this);
                }
                
                // 인덱스 업데이트
                updateGalleryIndices();
            }
            
            this.classList.remove('drag-over');
            return false;
        }
        
        function handleDragEnd(e) {
            this.classList.remove('dragging');
            
            // 모든 drag-over 클래스 제거
            const items = document.querySelectorAll('.gallery-item');
            items.forEach(item => {
                item.classList.remove('drag-over');
            });
            
            draggedItem = null;
        }
        
        function updateGalleryIndices() {
            const items = document.querySelectorAll('.gallery-item');
            items.forEach((item, index) => {
                item.setAttribute('data-index', index);
                
                // 삭제 버튼 onclick 업데이트
                const deleteBtn = item.querySelector('.control-btn');
                if (deleteBtn) {
                    deleteBtn.setAttribute('onclick', `deleteGalleryImage(${index})`);
                }
                
                // 크기 버튼 onclick 업데이트
                const sizeButtons = item.querySelectorAll('.size-btn');
                sizeButtons.forEach((btn, btnIndex) => {
                    const size = btnIndex === 0 ? 'small' : 'tall';
                    btn.setAttribute('onclick', `changeImageSize(${index}, '${size}')`);
                });
            });
        }
        
        function changeImageSize(index, size) {
            const items = document.querySelectorAll('.gallery-item');
            const item = items[index];
            
            if (!item) return;
            
            // 기존 크기 클래스 제거
            item.classList.remove('size-small', 'size-tall');
            // 새 크기 클래스 추가
            item.classList.add('size-' + size);
            item.setAttribute('data-size', size);
            
            // 버튼 활성화 상태 업데이트
            const sizeButtons = item.querySelectorAll('.size-btn');
            sizeButtons.forEach(btn => {
                btn.classList.remove('active');
                if (btn.textContent === (size === 'small' ? '가로' : '세로')) {
                    btn.classList.add('active');
                }
            });
        }
        
        function saveGalleryOrder() {
            const items = document.querySelectorAll('.gallery-item');
            const galleryData = [];
            
            items.forEach(item => {
                const img = item.querySelector('img');
                const size = item.getAttribute('data-size') || 'small';
                
                if (img && img.src) {
                    // 상대 경로로 변환
                    const src = img.src.replace(window.location.origin + '/', '');
                    const relativePath = (window.currentSlug && src.startsWith(window.currentSlug + '/')) ? src.substring(window.currentSlug.length + 1) : src;
                    galleryData.push({
                        path: relativePath,
                        size: size
                    });
                }
            });
            
            // 서버에 저장
            fetch('/admin/save_gallery_order', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(withSlug({
                    gallery_data: galleryData
                }))
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    alert('갤러리 순서와 크기가 저장되었습니다!');
                } else {
                    alert('저장 실패: ' + data.message);
                }
            })
            .catch(error => {
                console.error('저장 오류:', error);
                alert('저장 중 오류가 발생했습니다.');
            });
        }
</script>
</body>
</html>
'''

# 관리자 로그인 템플릿
ADMIN_LOGIN_TEMPLATE = '''
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>관리자 로그인</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: 'Malgun Gothic', sans-serif; background: #f7fafc; display: flex; align-items: center; justify-content: center; min-height: 100vh; }
        .login-card { background: white; padding: 30px; border-radius: 12px; box-shadow: 0 4px 16px rgba(0,0,0,0.12); width: 100%; max-width: 360px; }
        .login-card h1 { font-size: 22px; margin-bottom: 20px; color: #2d3748; text-align: center; }
        .login-card form { display: flex; flex-direction: column; gap: 16px; }
        .login-card label { font-weight: 600; color: #4a5568; font-size: 14px; }
        .login-card input { padding: 12px 14px; border: 1px solid #cbd5e0; border-radius: 8px; font-size: 14px; transition: border-color 0.2s ease; }
        .login-card input:focus { outline: none; border-color: #3182ce; box-shadow: 0 0 0 3px rgba(49, 130, 206, 0.15); }
        .btn-submit { background: #3182ce; color: white; border: none; border-radius: 8px; padding: 12px; font-size: 15px; font-weight: 600; cursor: pointer; transition: background 0.2s ease; }
        .btn-submit:hover { background: #2b6cb0; }
        .flash { padding: 12px 14px; border-radius: 8px; margin-bottom: 16px; font-size: 14px; }
        .flash-success { background: #f0fff4; color: #276749; border: 1px solid #9ae6b4; }
        .flash-error { background: #fff5f5; color: #c53030; border: 1px solid #feb2b2; }
    </style>
</head>
<body>
    <div class="login-card">
        <h1>관리자 로그인</h1>
        {% with messages = get_flashed_messages(with_categories=true) %}
            {% if messages %}
                {% for category, message in messages %}
                    <div class="flash flash-{{ 'success' if category == 'success' else 'error' }}">{{ message }}</div>
                {% endfor %}
            {% endif %}
        {% endwith %}
        <form method="POST">
            <input type="hidden" name="next" value="{{ next_url }}">
            <div>
                <label for="password">비밀번호</label>
                <input type="password" id="password" name="password" placeholder="비밀번호를 입력하세요" required autocomplete="current-password">
            </div>
            <button type="submit" class="btn-submit">로그인</button>
        </form>
    </div>
</body>
</html>
'''

# 방명록 관리 페이지 HTML 템플릿
RSVP_ADMIN_TEMPLATE = '''
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>RSVP 관리 - 결혼식 청첩장</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: 'Malgun Gothic', sans-serif; background: #f5f5f5; color: #2d3748; }
        .container { max-width: 1200px; margin: 0 auto; padding: 20px; }
        .header { background: #fff; padding: 20px; margin-bottom: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.08); }
        .header h1 { font-size: 28px; margin-bottom: 8px; color: #2d3748; }
        .header p { color: #718096; }
        .invitation-controls { margin-top: 15px; display: flex; flex-wrap: wrap; gap: 12px; align-items: center; }
        .invitation-controls label { font-weight: 600; color: #4a5568; }
        .invitation-controls select { padding: 10px 12px; border: 1px solid #cbd5e0; border-radius: 6px; font-size: 14px; min-width: 220px; }
        .btn { padding: 10px 18px; border: none; border-radius: 6px; font-size: 14px; font-weight: 600; cursor: pointer; text-decoration: none; display: inline-block; }
        .btn { background: #3182ce; color: #fff; }
        .btn:hover { background: #2b6cb0; }
        .btn-secondary { background: #4a5568; color: #fff; }
        .btn-secondary:hover { background: #2d3748; }
        .btn-danger { background: #e53e3e; color: #fff; }
        .btn-danger:hover { background: #c53030; }
        .alert { padding: 10px 15px; margin-bottom: 20px; border-radius: 6px; border: 1px solid transparent; }
        .alert-success { background: #f0fff4; border-color: #9ae6b4; color: #276749; }
        .alert-error { background: #fff5f5; border-color: #feb2b2; color: #c53030; }
        .stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 18px; margin-bottom: 20px; }
        .stat-card { background: #fff; border-radius: 10px; padding: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.06); text-align: center; }
        .stat-number { font-size: 2.2rem; font-weight: 700; color: #2b6cb0; }
        .stat-label { margin-top: 8px; color: #718096; font-size: 0.95rem; }
        .section { background: #fff; border-radius: 10px; padding: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.08); }
        .section h2 { font-size: 20px; margin-bottom: 16px; color: #2d3748; }
        .table-wrapper { overflow-x: auto; }
        table { width: 100%; border-collapse: collapse; font-size: 14px; }
        thead { background: #edf2f7; }
        th, td { padding: 12px 14px; border-bottom: 1px solid #e2e8f0; text-align: left; }
        th { font-weight: 700; color: #2d3748; }
        tbody tr:hover { background: #f7fafc; }
        .badge { display: inline-flex; align-items: center; padding: 4px 8px; border-radius: 999px; font-size: 12px; font-weight: 600; }
        .badge.side-groom { background: rgba(66, 153, 225, 0.1); color: #2b6cb0; }
        .badge.side-bride { background: rgba(236, 72, 153, 0.12); color: #b83280; }
        .badge.meal-planned { background: rgba(56, 161, 105, 0.12); color: #2f855a; }
        .badge.meal-not_planned { background: rgba(237, 137, 54, 0.15); color: #dd6b20; }
        .badge.meal-undecided { background: rgba(113, 128, 150, 0.12); color: #4a5568; }
        .no-entries { text-align: center; color: #718096; padding: 48px 0; font-style: italic; }
        .actions { display: flex; gap: 8px; flex-wrap: wrap; }
        @media (max-width: 640px) {
            .invitation-controls { flex-direction: column; align-items: flex-start; }
            table { font-size: 13px; }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📝 참석 의사 전달 관리</h1>
            <p>전달받은 참석 정보를 확인하고 관리할 수 있습니다.</p>
            <div class="invitation-controls">
                <label for="rsvp-invitation-select">청첩장 선택</label>
                <select id="rsvp-invitation-select">
                    {% for invitation in invitations %}
                    <option value="{{ invitation.slug }}" {% if invitation.slug == selected_slug %}selected{% endif %}>{{ invitation.name or invitation.slug }}{% if invitation.slug == default_slug %} (기본){% endif %}</option>
                    {% endfor %}
                </select>
                <a href="/admin?slug={{ selected_slug }}" class="btn btn-secondary">← 관리자 페이지</a>
                <a id="rsvp-preview-link" href="/{{ selected_slug or '' }}" class="btn" target="_blank">📱 청첩장 보기</a>
                <a href="/admin/logout" class="btn btn-danger">🔓 로그아웃</a>
            </div>
        </div>

        {% with messages = get_flashed_messages(with_categories=true) %}
            {% if messages %}
                {% for category, message in messages %}
                    <div class="alert alert-{{ 'success' if category == 'success' else 'error' }}">
                        {{ message }}
                    </div>
                {% endfor %}
            {% endif %}
        {% endwith %}

        <div class="stats">
            <div class="stat-card">
                <div class="stat-number">{{ total_entries }}</div>
                <div class="stat-label">총 접수 건수</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{{ total_attendees }}</div>
                <div class="stat-label">예상 참석 인원</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{{ side_stats.groom }}</div>
                <div class="stat-label">신랑측 접수</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{{ side_stats.bride }}</div>
                <div class="stat-label">신부측 접수</div>
            </div>
        </div>

        <div class="section">
            <h2>참석 의사 목록</h2>

            {% if rsvp_entries %}
            <div class="table-wrapper">
                <table class="rsvp-table">
                    <thead>
                        <tr>
                            <th>#</th>
                            <th>전달 대상</th>
                            <th>성함</th>
                            <th>참석 인원</th>
                            <th>동행인</th>
                            <th>식사 여부</th>
                            <th>접수 시각</th>
                            <th>관리</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for entry in rsvp_entries %}
                        <tr>
                            <td>{{ entry.id }}</td>
                            <td><span class="badge side-{{ entry.side }}">{{ entry.side_display }}</span></td>
                            <td>{{ entry.name }}</td>
                            <td>{{ entry.attendees }}</td>
                            <td>{{ entry.companion or '-' }}</td>
                            <td><span class="badge meal-{{ entry.meal }}">{{ entry.meal_display }}</span></td>
                            <td>{{ entry.submitted_display }}</td>
                            <td>
                                <div class="actions">
                                    <form method="POST" action="/admin/rsvp/delete/{{ entry.id }}?slug={{ selected_slug }}" onsubmit="return confirm('이 참석 정보를 삭제하시겠습니까?')">
                                        <button type="submit" class="btn btn-danger">삭제</button>
                                    </form>
                                </div>
                            </td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
            {% else %}
            <div class="no-entries">아직 전달된 참석 의사 정보가 없습니다.</div>
            {% endif %}
        </div>
    </div>
    <script>
        const rsvpSelect = document.getElementById('rsvp-invitation-select');
        const rsvpPreviewLink = document.getElementById('rsvp-preview-link');
        if (rsvpSelect) {
            if (rsvpPreviewLink) {
                rsvpPreviewLink.href = `/${rsvpSelect.value}`;
            }
            rsvpSelect.addEventListener('change', function() {
                window.location.href = `/admin/rsvp?slug=${encodeURIComponent(this.value)}`;
            });
        }
    </script>
</body>
</html>
'''

VISITS_ADMIN_TEMPLATE = '''
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>방문 로그 관리 - 결혼식 청첩장</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: 'Malgun Gothic', sans-serif; background: #f5f5f5; color: #2d3748; }
        .container { max-width: 1200px; margin: 0 auto; padding: 20px; }
        .header { background: #fff; padding: 20px; margin-bottom: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.08); }
        .header h1 { font-size: 28px; margin-bottom: 8px; color: #2d3748; }
        .header p { color: #718096; }
        .invitation-controls { margin-top: 15px; display: flex; flex-wrap: wrap; gap: 12px; align-items: center; }
        .invitation-controls label { font-weight: 600; color: #4a5568; }
        .invitation-controls select { padding: 10px 12px; border: 1px solid #cbd5e0; border-radius: 6px; font-size: 14px; min-width: 220px; }
        .btn { padding: 10px 18px; border: none; border-radius: 6px; font-size: 14px; font-weight: 600; cursor: pointer; text-decoration: none; display: inline-block; background: #3182ce; color: #fff; }
        .btn:hover { background: #2b6cb0; }
        .btn-secondary { background: #4a5568; }
        .btn-secondary:hover { background: #2d3748; }
        .btn-danger { background: #e53e3e; }
        .btn-danger:hover { background: #c53030; }
        .alert { padding: 10px 15px; margin-bottom: 20px; border-radius: 6px; border: 1px solid transparent; }
        .alert-success { background: #f0fff4; border-color: #9ae6b4; color: #276749; }
        .alert-error { background: #fff5f5; border-color: #feb2b2; color: #c53030; }
        .actions { display: flex; gap: 8px; flex-wrap: wrap; }
        .stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 18px; margin-bottom: 20px; }
        .stat-card { background: #fff; border-radius: 10px; padding: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.06); text-align: center; }
        .stat-number { font-size: 2rem; font-weight: 700; color: #2b6cb0; }
        .stat-label { margin-top: 8px; color: #718096; font-size: 0.95rem; }
        .section { background: #fff; border-radius: 10px; padding: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.08); }
        .section h2 { font-size: 20px; margin-bottom: 16px; color: #2d3748; }
        .table-wrapper { overflow-x: auto; }
        table { width: 100%; border-collapse: collapse; font-size: 14px; }
        thead { background: #edf2f7; }
        th, td { padding: 12px 14px; border-bottom: 1px solid #e2e8f0; text-align: left; vertical-align: top; }
        th { font-weight: 700; color: #2d3748; }
        tbody tr:hover { background: #f7fafc; }
        .badge { display: inline-flex; align-items: center; padding: 4px 8px; border-radius: 999px; font-size: 12px; font-weight: 600; }
        .badge-ip { background: rgba(66, 153, 225, 0.1); color: #2b6cb0; }
        .badge-count { background: rgba(56, 161, 105, 0.12); color: #2f855a; }
        details { background: #f7fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 10px 14px; margin-top: 6px; }
        details > summary { cursor: pointer; font-weight: 600; color: #2d3748; }
        details ul { margin-top: 8px; padding-left: 18px; color: #4a5568; }
        .user-agent { margin-top: 6px; font-size: 12px; color: #718096; }
        .no-entries { text-align: center; color: #718096; padding: 48px 0; font-style: italic; }
        @media (max-width: 640px) {
            .invitation-controls { flex-direction: column; align-items: flex-start; }
            table { font-size: 13px; }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>👣 방문 로그 관리</h1>
            <p>초대장 페이지에 접속한 방문 기록을 IP별로 확인할 수 있습니다.</p>
            <div class="invitation-controls">
                <label for="visits-invitation-select">청첩장 선택</label>
                <select id="visits-invitation-select">
                    {% for invitation in invitations %}
                    <option value="{{ invitation.slug }}" {% if invitation.slug == selected_slug %}selected{% endif %}>{{ invitation.name or invitation.slug }}{% if invitation.slug == default_slug %} (기본){% endif %}</option>
                    {% endfor %}
                </select>
                <a href="/admin?slug={{ selected_slug }}" class="btn btn-secondary">← 관리자 페이지</a>
                <a id="visits-preview-link" href="/{{ selected_slug or '' }}" class="btn" target="_blank">📱 청첩장 보기</a>
                <form method="POST" action="/admin/visits/clear?slug={{ selected_slug }}" onsubmit="return confirm('이 청첩장의 방문 로그를 모두 삭제하시겠습니까?')">
                    <button type="submit" class="btn btn-danger">🧹 로그 초기화</button>
                </form>
                <a href="/admin/logout" class="btn btn-danger">🔓 로그아웃</a>
            </div>
        </div>

        {% with messages = get_flashed_messages(with_categories=true) %}
            {% if messages %}
                {% for category, message in messages %}
                    <div class="alert alert-{{ 'success' if category == 'success' else 'error' }}">
                        {{ message }}
                    </div>
                {% endfor %}
            {% endif %}
        {% endwith %}

        <div class="stats">
            <div class="stat-card">
                <div class="stat-number">{{ unique_ip_count }}</div>
                <div class="stat-label">고유 IP 수</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{{ total_visit_count }}</div>
                <div class="stat-label">총 방문 수</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{{ recent_24h_count }}</div>
                <div class="stat-label">최근 24시간 방문</div>
            </div>
        </div>

        <div class="section">
            <h2>방문 로그</h2>

            {% if visit_entries %}
            <div class="table-wrapper">
                <table class="visit-table">
                    <thead>
                        <tr>
                            <th>IP</th>
                            <th>총 방문</th>
                            <th>최근 방문</th>
                            <th>첫 방문</th>
                            <th>최근 경로</th>
                            <th>기기/브라우저</th>
                            <th>상세 기록</th>
                            <th>관리</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for entry in visit_entries %}
                        <tr>
                            <td><span class="badge badge-ip">{{ entry.ip }}</span></td>
                            <td><span class="badge badge-count">{{ entry.count }}</span></td>
                            <td>{{ entry.last_seen_display }}</td>
                            <td>{{ entry.first_seen_display }}</td>
                            <td>{{ entry.last_path or '-' }}</td>
                            <td>
                                {% if entry.user_agents %}
                                    <div class="user-agent">{{ entry.user_agents[0] }}</div>
                                    {% if entry.user_agents|length > 1 %}
                                        <details>
                                            <summary>다른 기기 ({{ entry.user_agents|length - 1 }})</summary>
                                            <ul>
                                                {% for ua in entry.user_agents[1:] %}
                                                <li>{{ ua }}</li>
                                                {% endfor %}
                                            </ul>
                                        </details>
                                    {% endif %}
                                {% else %}
                                    -
                                {% endif %}
                            </td>
                            <td>
                                <details>
                                    <summary>최근 방문 {{ entry.visits|length }}건</summary>
                                    <ul>
                                        {% for visit in entry.visits %}
                                        <li>{{ visit.timestamp_display }} ({{ visit.path }})</li>
                                        {% endfor %}
                                    </ul>
                                </details>
                            </td>
                            <td>
                                <form method="POST" action="/admin/visits/delete?slug={{ selected_slug }}" onsubmit="return confirm('해당 IP의 로그를 삭제하시겠습니까?')">
                                    <input type="hidden" name="ip" value="{{ entry.ip }}">
                                    <button type="submit" class="btn btn-danger">삭제</button>
                                </form>
                            </td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
            {% else %}
            <div class="no-entries">아직 기록된 방문 로그가 없습니다.</div>
            {% endif %}
        </div>
    </div>
    <script>
        const visitSelect = document.getElementById('visits-invitation-select');
        const visitPreviewLink = document.getElementById('visits-preview-link');
        if (visitSelect) {
            if (visitPreviewLink) {
                visitPreviewLink.href = `/${visitSelect.value}`;
            }
            visitSelect.addEventListener('change', function() {
                window.location.href = `/admin/visits?slug=${encodeURIComponent(this.value)}`;
            });
        }
    </script>
</body>
</html>
'''

GUESTBOOK_ADMIN_TEMPLATE = '''
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>방명록 관리 - 결혼식 청첩장</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: 'Malgun Gothic', sans-serif; background: #f5f5f5; }
        .container { max-width: 1200px; margin: 0 auto; padding: 20px; }
        .header { background: white; padding: 20px; margin-bottom: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .header h1 { color: #333; }
        .header p { color: #666; margin-top: 10px; }
        .section { background: white; margin-bottom: 20px; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .section h2 { color: #333; margin-bottom: 15px; padding-bottom: 10px; border-bottom: 2px solid #eee; }
        .btn { padding: 10px 20px; background: #007bff; color: white; border: none; border-radius: 4px; cursor: pointer; font-size: 14px; text-decoration: none; display: inline-block; }
        .btn:hover { background: #0056b3; }
        .btn-danger { background: #dc3545; }
        .btn-danger:hover { background: #c82333; }
        .btn-secondary { background: #6c757d; }
        .btn-secondary:hover { background: #545b62; }
        .alert { padding: 10px 15px; margin-bottom: 20px; border-radius: 4px; }
        .alert-success { background: #d4edda; color: #155724; border: 1px solid #c3e6cb; }
        .alert-error { background: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; }
        .guestbook-entry { border: 1px solid #ddd; border-radius: 8px; padding: 20px; margin-bottom: 15px; background: white; }
        .entry-header { display: flex; justify-content: between; align-items: center; margin-bottom: 10px; }
        .entry-info { display: flex; gap: 15px; align-items: center; }
        .entry-name { font-weight: bold; color: #333; font-size: 16px; }
        .entry-date { color: #666; font-size: 14px; }
        .entry-id { background: #f8f9fa; color: #666; padding: 2px 6px; border-radius: 3px; font-size: 12px; }
        .entry-message { color: #555; line-height: 1.6; margin: 10px 0; }
        .entry-actions { margin-top: 15px; }
        .stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin-bottom: 20px; }
        .stat-card { background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); text-align: center; }
        .stat-number { font-size: 2em; font-weight: bold; color: #007bff; }
        .stat-label { color: #666; margin-top: 5px; }
        .no-entries { text-align: center; color: #666; font-style: italic; padding: 40px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>💬 방명록 관리</h1>
            <p>방문자들이 남긴 방명록을 관리할 수 있습니다.</p>
            <div class="invitation-controls">
                <label for="guestbook-invitation-select">청첩장 선택</label>
                <select id="guestbook-invitation-select">
                    {% for invitation in invitations %}
                    <option value="{{ invitation.slug }}" {% if invitation.slug == current_slug %}selected{% endif %}>{{ invitation.name or invitation.slug }}{% if invitation.slug == default_slug %} (기본){% endif %}</option>
                    {% endfor %}
                </select>
                <a href="/admin?slug={{ current_slug }}" class="btn btn-secondary">← 관리자 페이지</a>
                <a id="guestbook-preview-link" href="/{{ current_slug or '' }}" class="btn" target="_blank">📱 청첩장 보기</a>
            </div>
        </div>

        {% with messages = get_flashed_messages(with_categories=true) %}
            {% if messages %}
                {% for category, message in messages %}
                    <div class="alert alert-{{ 'success' if category == 'success' else 'error' }}">
                        {{ message }}
                    </div>
                {% endfor %}
            {% endif %}
        {% endwith %}

        <!-- 통계 -->
        <div class="stats">
            <div class="stat-card">
                <div class="stat-number">{{ guestbook|length }}</div>
                <div class="stat-label">전체 방명록</div>
            </div>
        </div>

        <!-- 방명록 목록 -->
        <div class="section">
            <h2>방명록 목록</h2>
            
            {% if guestbook %}
                {% for entry in guestbook %}
                <div class="guestbook-entry">
                    <div class="entry-header">
                        <div class="entry-info">
                            <span class="entry-id">#{{ entry.id }}</span>
                            <span class="entry-name">{{ entry.name }}</span>
                            <span class="entry-date">{{ entry.date }}</span>
                        </div>
                    </div>
                    <div class="entry-message">{{ entry.message|safe }}</div>
                    <div class="entry-actions">
                        <form method="POST" action="/admin/guestbook/delete/{{ entry.id }}?slug={{ current_slug }}" style="display: inline;" 
                              onsubmit="return confirm('이 방명록을 삭제하시겠습니까?')">
                            <button type="submit" class="btn btn-danger">삭제</button>
                        </form>
                    </div>
                </div>
                {% endfor %}
            {% else %}
                <div class="no-entries">
                    아직 작성된 방명록이 없습니다.
                </div>
            {% endif %}
        </div>
    <script>
        const guestbookSelect = document.getElementById('guestbook-invitation-select');
        const guestbookPreviewLink = document.getElementById('guestbook-preview-link');
        if (guestbookSelect) {
            if (guestbookPreviewLink) {
                guestbookPreviewLink.href = `/${guestbookSelect.value}`;
            }
            guestbookSelect.addEventListener('change', function() {
                window.location.href = `/admin/guestbook?slug=${encodeURIComponent(this.value)}`;
            });
        }
    </script>
    </div>
</body>
</html>
'''

# 방명록 관련 API
@app.route('/api/guestbook', methods=['GET'])
def get_guestbook():
    """방명록 목록 조회"""
    try:
        slug = resolve_invitation_slug()
        if slug and not invitation_exists(slug):
            slug = None
        if not slug:
            slug = get_default_invitation_slug()

        guestbook = load_guestbook_entries(slug)
        guestbook.sort(key=lambda x: x.get('timestamp', 0), reverse=True)
        return jsonify({'success': True, 'data': guestbook, 'slug': slug})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})
@app.route('/api/guestbook', methods=['POST'])
def add_guestbook():
    """방명록 작성"""
    try:
        data = request.get_json() or {}
        slug = data.get('slug') or resolve_invitation_slug()

        if slug and not invitation_exists(slug):
            return jsonify({'success': False, 'message': '청첩장을 찾을 수 없습니다.'})
        if not slug:
            slug = get_default_invitation_slug()

        name = (data.get('name') or '').strip()
        message = (data.get('message') or '').strip()
        password = (data.get('password') or '').strip()

        if not name or len(name) > 20:
            return jsonify({'success': False, 'message': '이름을 1-20자로 입력해주세요.'})
        if not message or len(message) > 500:
            return jsonify({'success': False, 'message': '메시지를 1-500자로 입력해주세요.'})
        if not password or len(password) < 4:
            return jsonify({'success': False, 'message': '비밀번호를 4자 이상 입력해주세요.'})

        guestbook = load_guestbook_entries(slug)
        import time
        from datetime import datetime

        next_id = max([entry.get('id', 0) for entry in guestbook], default=0) + 1
        new_entry = {
            'id': next_id,
            'name': name,
            'message': message.replace('\n', '<br>'),
            'password': password,
            'date': datetime.now().strftime('%Y.%m.%d'),
            'timestamp': int(time.time())
        }

        guestbook.append(new_entry)
        save_guestbook_entries(slug, guestbook)

        return jsonify({'success': True, 'message': '방명록이 작성되었습니다.', 'entry': new_entry, 'slug': slug})

    except Exception as e:
        return jsonify({'success': False, 'message': f'오류가 발생했습니다: {str(e)}'})
@app.route('/api/guestbook/<int:entry_id>', methods=['DELETE'])
def delete_guestbook(entry_id):
    """방명록 삭제"""
    try:
        data = request.get_json() or {}
        slug = data.get('slug') or resolve_invitation_slug()

        if slug and not invitation_exists(slug):
            return jsonify({'success': False, 'message': '청첩장을 찾을 수 없습니다.'})
        if not slug:
            slug = get_default_invitation_slug()

        password = (data.get('password') or '').strip()
        if not password:
            return jsonify({'success': False, 'message': '비밀번호를 입력해주세요.'})

        guestbook = load_guestbook_entries(slug)
        entry_to_delete = None
        for i, entry in enumerate(guestbook):
            if entry.get('id') == entry_id:
                entry_to_delete = i
                break

        if entry_to_delete is None:
            return jsonify({'success': False, 'message': '방명록을 찾을 수 없습니다.'})

        if guestbook[entry_to_delete].get('password') != password:
            return jsonify({'success': False, 'message': '비밀번호가 일치하지 않습니다.'})

        guestbook.pop(entry_to_delete)
        save_guestbook_entries(slug, guestbook)

        return jsonify({'success': True, 'message': '방명록이 삭제되었습니다.'})

    except Exception as e:
        return jsonify({'success': False, 'message': f'오류가 발생했습니다: {str(e)}'})


@app.route('/api/rsvp', methods=['GET'])
def get_rsvp_entries_api():
    try:
        slug = resolve_invitation_slug()
        if slug and not invitation_exists(slug):
            slug = None

        if not slug:
            slug = get_default_invitation_slug()

        if not slug:
            return jsonify({'success': False, 'message': '청첩장을 찾을 수 없습니다.'}), 404

        entries = load_rsvp_entries(slug)
        entries.sort(key=lambda item: item.get('submitted_at', ''), reverse=True)

        return jsonify({'success': True, 'data': entries, 'slug': slug})
    except Exception as e:
        app.logger.error(f'RSVP 조회 오류: {e}', exc_info=True)
        return jsonify({'success': False, 'message': f'조회 중 오류가 발생했습니다: {str(e)}'}), 500


@app.route('/api/rsvp', methods=['POST'])
def submit_rsvp():
    try:
        data = request.get_json() or {}
        slug = resolve_invitation_slug()

        if slug and not invitation_exists(slug):
            slug = None

        if not slug:
            slug = get_default_invitation_slug()

        if not slug:
            return jsonify({'success': False, 'message': '청첩장을 찾을 수 없습니다.'}), 404

        side = (data.get('side') or '').strip().lower()
        if side not in {'groom', 'bride'}:
            side = 'groom'

        name = (data.get('name') or '').strip()
        if not name:
            return jsonify({'success': False, 'message': '성함을 입력해주세요.'}), 400

        attendees = data.get('attendees', 1)
        try:
            attendees = max(1, int(attendees))
        except (TypeError, ValueError):
            attendees = 1

        companion = (data.get('companion') or '').strip()
        meal = (data.get('meal') or '').strip().lower()
        if meal not in {'planned', 'not_planned', 'undecided'}:
            meal = 'planned'

        entries = load_rsvp_entries(slug)
        next_id = max((entry.get('id', 0) for entry in entries), default=0) + 1

        entry = {
            'id': next_id,
            'side': side,
            'name': name,
            'attendees': attendees,
            'companion': companion,
            'meal': meal,
            'submitted_at': datetime.utcnow().isoformat()
        }

        entries.append(entry)
        save_rsvp_entries(slug, entries)

        return jsonify({'success': True, 'message': '참석 의사가 전달되었습니다.', 'entry': entry, 'slug': slug})
    except Exception as e:
        app.logger.error(f'RSVP 저장 오류: {e}', exc_info=True)
        return jsonify({'success': False, 'message': '요청 처리 중 오류가 발생했습니다.'}), 500

@app.route('/api/map-settings', methods=['GET'])
def get_map_settings():
    """지도 설정 조회"""
    try:
        slug = resolve_invitation_slug()
        if slug and not invitation_exists(slug):
            slug = None

        if not slug:
            slug = get_default_invitation_slug()

        config = load_config(slug) if slug else {}
        map_settings = config.get('map_settings') or {}

        if not map_settings:
            map_settings = {
                'venueName': 'JK아트컨벤션',
                'venueAddress': '서울특별시 영등포구 문래동3가 55-16',
                'venueDetail': '문래역 SK리더스뷰 4층',
                'venuePhone': '',
                'mapImage': '',
                'subwayInfo': '2호선 문래역 1번 출구 도보 3분',
                'busInfo': '간선버스: 160, 503, 600번\n지선버스: 5615, 6512번',
                'parkingInfo': 'SK리더스뷰 지하주차장 이용 (2시간 무료)\n주차권은 안내데스크에서 수령해주세요'
            }

        return jsonify({'success': True, 'settings': map_settings, 'slug': slug})
    except Exception as e:
        return jsonify({'success': False, 'message': f'설정 조회 중 오류가 발생했습니다: {str(e)}'})

@app.route('/api/map-settings', methods=['POST'])
def save_map_settings():
    """지도 설정 저장"""
    try:
        data = request.get_json() or {}
        slug = resolve_invitation_slug()

        if not slug or not invitation_exists(slug):
            return jsonify({'success': False, 'message': '선택된 청첩장을 찾을 수 없습니다.'})

        required_fields = ['venueName', 'venueAddress']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'success': False, 'message': f'{field}는 필수 입력 항목입니다.'})

        config = load_config(slug)
        config['map_settings'] = {
            'venueName': data.get('venueName', ''),
            'venueAddress': data.get('venueAddress', ''),
            'venueDetail': data.get('venueDetail', ''),
            'venuePhone': data.get('venuePhone', ''),
            'mapImage': data.get('mapImage', ''),
            'subwayInfo': data.get('subwayInfo', ''),
            'busInfo': data.get('busInfo', ''),
            'parkingInfo': data.get('parkingInfo', '')
        }

        config.setdefault('meta', {})['updated_at'] = datetime.utcnow().isoformat()
        save_config(config, invitation_slug=slug)

        return jsonify({'success': True, 'message': '지도 설정이 저장되었습니다.', 'slug': slug})

    except Exception as e:
        return jsonify({'success': False, 'message': f'설정 저장 중 오류가 발생했습니다: {str(e)}'})

@app.route('/admin')
def admin_page():
    """관리자 페이지"""
    return send_file('admin.html')

if __name__ == '__main__':
    import socket
    
    # 현재 컴퓨터의 IP 주소 가져오기
    def get_local_ip():
        try:
            # 임시 소켓을 만들어 로컬 IP 주소 확인
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except:
            return "localhost"
    
    local_ip = get_local_ip()
    
    print("🎉 결혼식 청첩장 웹사이트를 시작합니다!")
    print("=" * 50)
    print("📱 로컬 접속:")
    print(f"   청첩장: http://localhost:8007")
    print(f"   관리자: http://localhost:8007/admin")
    print("")
    print("🌐 외부 접속 (같은 네트워크):")
    print(f"   청첩장: http://{local_ip}:8007")
    print(f"   관리자: http://{local_ip}:8007/admin")
    print("")
    print("📱 모바일에서도 위 주소로 접속 가능합니다!")
    print("=" * 50)
    print("⏹️  종료하려면 Ctrl+C를 누르세요")
    print("")
    
    app.run(debug=True, host='0.0.0.0', port=8007)
