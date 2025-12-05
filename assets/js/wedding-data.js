// 결혼식 데이터 설정
// 이 파일의 데이터를 수정하여 청첩장 내용을 변경할 수 있습니다.

const weddingData = {
  // 기본 정보
  wedding_info: {
    groom_name: "혁재",
    bride_name: "진주",
    wedding_date: "2026.02.21",
    wedding_time: "토요일 오후 16시 00분",
    wedding_venue: "용산 국방컨벤션 1층 에메랄드홀",
    wedding_address: "서울 용산구 이태원로 22",
  },

  // 가족 정보
  family_info: {
    groom_father: "권오쥰",
    groom_mother: "심성희",
    bride_father: "배명규",
    bride_mother: "김숙향",
  },

  // 메시지
  messages: {
    poem_message: "", // 시 한구절 (필요시 입력)
    invitation_message: "", // 초대장 메시지 (필요시 입력)
    outro_message:
      "응원하고 격려해주신 모든 분들께 감사드리며\n행복하게 잘 살겠습니다.", // 마무리 메시지
  },

  // 이미지 경로
  images: {
    main_photo: "assets/images/main.png",
    invitation_photo: "", // 초대장 사진 (필요시 입력)
    outro_photo: "assets/images/last2.webp", // 마무리 사진 (필요시 입력)
  },

  // 교통 정보
  transportation: {
    subway: "", // 지하철 안내 (필요시 입력)
    bus: "", // 버스 안내 (필요시 입력)
    parking: "", // 주차 안내 (필요시 입력)
  },

  // 지도 설정
  map_settings: {
    mapImage: "assets/images/location_new.jpg", // 지도 이미지 경로
    subwayInfo: "", // 지하철 정보 (필요시 입력)
    busInfo: "", // 버스 정보 (필요시 입력)
    parkingInfo: "", // 주차 정보 (필요시 입력)
  },

  // 계좌 정보
  account_info: {
    groom_accounts: [
      {
        bank: "하나",
        number: "355-910263-14507 ",
        name: "권혁재",
      },
      {
        bank: "농협",
        number: "302-0737-6647-91",
        name: "권오쥰",
      },
      {
        bank: "새마을금고",
        number: "9003-2988-5045-3",
        name: "심성희",
      },
    ],
    bride_accounts: [
      {
        bank: "카카오뱅크",
        number: "3333-35-7148524",
        name: "배진주",
      },
      {
        bank: "농협",
        number: "352-2066-2611-03",
        name: "배명구",
      },
      {
        bank: "국민",
        number: "247901-04-378659",
        name: "김숙향",
      },
    ],
  },

  // 연락처 정보
  contacts: {
    groom: {
      name: "권혁재",
      phone: "010-2114-7883",
    },
    bride: {
      name: "배진주",
      phone: "010-5140-3725",
    },
  },

  // 갤러리 이미지 (배열)
  gallery_images: [
    "assets/images/gallery_webp/01.webp",
    "assets/images/gallery_webp/02.webp",
    "assets/images/gallery_webp/03.webp",
    "assets/images/gallery_webp/04.webp",
    "assets/images/gallery_webp/05.webp",
    "assets/images/gallery_webp/06.webp",
    "assets/images/gallery_webp/07.webp",
    "assets/images/gallery_webp/08.webp",
    "assets/images/gallery_webp/09.webp",
    "assets/images/gallery_webp/10.webp",
    "assets/images/gallery_webp/11_main.webp",
    "assets/images/gallery_webp/12.webp",
    "assets/images/gallery_webp/13.webp",
    "assets/images/gallery_webp/14.webp",
    "assets/images/gallery_webp/15.webp",
    "assets/images/gallery_webp/16.webp",
    "assets/images/gallery_webp/17.webp",
    "assets/images/gallery_webp/18.webp",
    "assets/images/gallery_webp/19.webp",
    "assets/images/gallery_webp/20.webp",
    "assets/images/gallery_webp/21.webp",
    "assets/images/gallery_webp/22.webp",
    "assets/images/gallery_webp/23.webp",
    "assets/images/gallery_webp/24.webp",
    "assets/images/gallery_webp/25.webp",
    "assets/images/gallery_webp/26.webp",
    "assets/images/gallery_webp/27.webp",
  ],

  // 메타 정보
  meta: {
    thumbnail: "assets/images/main.png", // OG 이미지
  },

  // 배경음악 설정
  audio: {
    background_music: "assets/audio/up_ost.mp3", // 배경음악 파일 경로 (예: 'assets/audio/wedding-song.mp3')
    autoplay: true, // 자동 재생 여부
    loop: true, // 반복 재생 여부
    volume: 0.3, // 볼륨 (0.0 ~ 1.0, 0.3 = 30%)
  },
};

// 페이지 제목과 설명 생성
function generatePageTitle() {
  return `${weddingData.wedding_info.groom_name} ♥ ${weddingData.wedding_info.bride_name} 결혼합니다`;
}

function generatePageDescription() {
  const info = weddingData.wedding_info;
  const parts = [];
  if (info.wedding_date) parts.push(info.wedding_date);
  if (info.wedding_time) parts.push(info.wedding_time);
  if (info.wedding_venue) parts.push(info.wedding_venue);
  return parts.join(" ") || generatePageTitle();
}
