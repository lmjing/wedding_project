# 결혼식 청첩장 웹사이트

최도현 ♥ 이하나 결혼식 청첩장 웹사이트입니다.

## 프로젝트 구조

```
wedding_invitation/
├── index.html              # 메인 HTML 파일
├── assets/
│   ├── css/
│   │   └── styles.css      # 스타일시트
│   ├── js/
│   │   └── script.js       # JavaScript 기능
│   ├── images/             # 이미지 파일들
│   │   ├── gallery/        # 갤러리 이미지
│   │   └── placeholder.svg # 플레이스홀더 이미지
│   └── audio/              # 배경음악 파일
└── README.md               # 프로젝트 설명
```

## 주요 기능

1. **메인 소개**: 결혼식 날짜, 시간, 장소 정보
2. **카운트다운**: 결혼식까지 남은 시간 실시간 표시
3. **갤러리**: 신랑신부 사진들을 그리드 형태로 표시
4. **오시는 길**: 지도와 교통 정보
5. **예식 정보**: 포토부스, 식사, 주차 안내
6. **계좌 정보**: 축의금 계좌번호 (복사 기능 포함)
7. **방명록**: 축하 메시지 작성 및 조회
8. **공유 기능**: 카카오톡 공유, 링크 복사

## 사용 방법

1. 웹서버에 파일들을 업로드합니다.
2. `assets/images/` 폴더에 실제 이미지들을 추가합니다:
   - `main-photo.jpg`: 메인 사진
   - `invitation-photo.jpg`: 초대 사진
   - `photobooth.jpg`: 포토부스 사진
   - `outro-photo.jpg`: 마무리 사진
   - `gallery/` 폴더에 갤러리 이미지들
3. `assets/audio/` 폴더에 배경음악 파일을 추가합니다:
   - `piano_02.mp3`: 배경음악
4. 필요에 따라 HTML 내용을 수정합니다.

## 이미지 파일 목록

다음 이미지 파일들을 준비해주세요:

### 메인 이미지
- `assets/images/main-photo.jpg` (627x853 권장)
- `assets/images/invitation-photo.jpg`
- `assets/images/photobooth.jpg`
- `assets/images/outro-photo.jpg`

### 갤러리 이미지
- `assets/images/gallery/gallery1.jpg`
- `assets/images/gallery/gallery2.jpg`
- `assets/images/gallery/gallery3.jpg`
- `assets/images/gallery/gallery4.jpg`
- `assets/images/gallery/gallery5.jpg`
- `assets/images/gallery/gallery6.jpg`
- `assets/images/gallery/gallery7.jpg`
- `assets/images/gallery/gallery8.jpg`

### 아이콘 이미지
- `assets/images/icon_navermap_w48.png`
- `assets/images/icon_kakaonavi_w48.png`
- `assets/images/icon_tmap_w48.png`
- `assets/images/icon_flower_biz2.png`
- `assets/images/bg_paper_00.png` (배경 텍스처)

### 오디오 파일
- `assets/audio/piano_02.mp3` (배경음악)

## 커스터마이징

### 날짜 및 정보 변경
`index.html` 파일에서 다음 정보들을 수정할 수 있습니다:
- 결혼식 날짜 및 시간
- 신랑신부 이름
- 가족 정보
- 예식장 정보
- 계좌번호

### 스타일 변경
`assets/css/styles.css` 파일에서 색상, 폰트, 레이아웃을 수정할 수 있습니다.

### 기능 추가
`assets/js/script.js` 파일에서 추가 기능을 구현할 수 있습니다.

## 브라우저 호환성

- Chrome, Firefox, Safari, Edge 최신 버전 지원
- 모바일 브라우저 최적화
- 반응형 디자인 적용

## 라이선스

이 프로젝트는 개인적인 용도로 자유롭게 사용할 수 있습니다.
