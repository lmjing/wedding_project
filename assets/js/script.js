// 전역 변수
let countdownInterval;
let preloadedImages = new Map(); // 프리로드된 이미지 캐시
let preloadingProgress = 0;
let totalImagesToPreload = 0;

const invitationSlug =
  window.location.pathname.split("/").filter(Boolean)[0] || "";

// DOM이 로드된 후 실행
document.addEventListener("DOMContentLoaded", function () {
  initializeWebsite();
});

// 결혼식 데이터를 DOM에 주입
function injectWeddingData() {
  if (typeof weddingData === "undefined") {
    console.warn(
      "weddingData가 정의되지 않았습니다. wedding-data.js 파일을 확인해주세요."
    );
    return;
  }

  const data = weddingData;
  const info = data.wedding_info;
  const family = data.family_info;
  const messages = data.messages;
  const images = data.images;
  const transport = data.transportation;
  const mapSettings = data.map_settings;
  const accounts = data.account_info;
  const contacts = data.contacts;

  // 페이지 제목 및 메타 정보
  const pageTitle = generatePageTitle();
  const pageDescription = generatePageDescription();
  const ogImage =
    data.meta.thumbnail || images.main_photo || "assets/images/main-photo.jpg";

  document.title = pageTitle;
  updateMetaTag("og:title", pageTitle);
  updateMetaTag("og:description", pageDescription);
  updateMetaTag("og:image", ogImage);
  updateMetaTag("twitter:title", pageTitle);
  updateMetaTag("twitter:description", pageDescription);
  updateMetaTag("twitter:image", ogImage);

  // 신랑/신부 이름
  updateTextContent(".groom", info.groom_name);
  updateTextContent(".bride", info.bride_name);

  // 날짜/시간/장소
  updateTextContent(".datetime", info.wedding_date);
  const timeEl = document.querySelector(".datetime span");
  if (timeEl) timeEl.textContent = info.wedding_time;
  const venueEl = document.querySelector(".datetime div");
  if (venueEl) venueEl.textContent = info.wedding_venue;

  // 메인 사진
  const mainPhotoEl = document.querySelector(".intro-blend-image");
  if (mainPhotoEl && images.main_photo) {
    mainPhotoEl.src = images.main_photo;
    mainPhotoEl.alt = `${info.groom_name} ${info.bride_name} 사진`;
  }

  // 시 한구절
  if (messages.poem_message) {
    const poemEl = document.querySelector(".paragraph-wrap .text div");
    if (poemEl) poemEl.textContent = messages.poem_message;
  }

  // 초대장 메시지
  if (messages.invitation_message) {
    const invitationEl = document.querySelector(
      ".greetings-wrap .text.center div"
    );
    if (invitationEl) invitationEl.textContent = messages.invitation_message;
  }

  // 초대장 이미지
  if (images.invitation_photo) {
    const invitationMediaEl = document.querySelector(".greetings-wrap .image");
    if (invitationMediaEl) {
      invitationMediaEl.innerHTML = `<img src="${images.invitation_photo}" alt="초대장" style="width: 100%; height: auto;">`;
    }
  }

  // 가족 소개
  const membersWrap = document.querySelector(".members-wrap");
  if (membersWrap) {
    const groomFamily = membersWrap.querySelector("div:first-child");
    const brideFamily = membersWrap.querySelector("div:last-child");
    if (groomFamily) {
      groomFamily.innerHTML = `
                <span><span>${family.groom_father} <span>·</span></span> <span>${family.groom_mother}</span></span>
                <span class="relation"><span>의</span> <span>아들</span></span>
                <span class="lname">${info.groom_name}</span>
            `;
    }
    if (brideFamily) {
      brideFamily.innerHTML = `
                <span><span>${family.bride_father} <span>·</span></span> <span>${family.bride_mother}</span></span>
                <span class="relation"><span>의</span> <span>딸</span></span>
                <span class="lname">${info.bride_name}</span>
            `;
    }
  }

  // 지도 이미지
  if (mapSettings.mapImage) {
    const mapContainer = document.getElementById("zoomable-map");
    if (mapContainer) {
      mapContainer.innerHTML = `<img src="${mapSettings.mapImage}" alt="지도" style="width: 100%; height: auto; border-radius: 6px;">`;
    }
  }

  // 교통 정보
  if (mapSettings.subwayInfo || transport.subway) {
    const subwayEl = document.querySelector(
      ".waytocome-wrap .box:first-child .content div"
    );
    if (subwayEl)
      subwayEl.textContent = mapSettings.subwayInfo || transport.subway;
  }
  if (mapSettings.busInfo || transport.bus) {
    const busEl = document.querySelector(
      ".waytocome-wrap .box:nth-child(2) .content div"
    );
    if (busEl) busEl.textContent = mapSettings.busInfo || transport.bus;
  }
  if (mapSettings.parkingInfo || transport.parking) {
    const parkingEl = document.querySelector(
      ".waytocome-wrap .box:last-child .content div"
    );
    if (parkingEl)
      parkingEl.textContent = mapSettings.parkingInfo || transport.parking;
  }

  // 계좌 정보
  const accountWrap = document.querySelector(".c-account");
  if (accountWrap) {
    const insertBridgeAccountItems = (brideAccountItem, bride_accounts) => {
      if (brideAccountItem && bride_accounts.length > 0) {
        bride_accounts.forEach((account) => {
          const div = document.createElement("div");
          div.className = "text gothic";
          div.style.display = "none";
          div.style.height = "auto";

          div.innerHTML = `
                    <div class="inner">
                              <span><span class="bank">${account.bank}</span> <span>${account.number}</span></span><br>
                              <span>${account.name}</span>
                              </div>
                    <div>
                      <div
                        class="btn-action"
                      >
                        <svg viewBox="0.48 0.48 23.04 23.04" fill="#222F3D">
                          <path fill="none" d="M0 0h24v24H0z"></path>
                          <path
                            d="M16 1H4c-1.1 0-2 .9-2 2v14h2V3h12V1zm3 4H8c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h11c1.1 0 2-.9 2-2V7c0-1.1-.9-2-2-2zm0 16H8V7h11v14z"
                          ></path>
                        </svg>
                        복사
                      </div>`;
          const btn = div.querySelector(".btn-action");
          if (btn) {
            btn.setAttribute(
              "onclick",
              `copyAccount('${account.bank} ${account.number} ${account.name}')`
            );
          }
          brideAccountItem.appendChild(div);
        });
      }
    };
    // 신랑측 계좌
    const groomAccountItem = accountWrap.querySelector(".item:first-child");
    insertBridgeAccountItems(groomAccountItem, accounts.groom_accounts);

    // 신부측 계좌
    const brideAccountItem = accountWrap.querySelector(".item:last-child");
    insertBridgeAccountItems(brideAccountItem, accounts.bride_accounts);
  }

  // 연락처 정보
  const contactModal = document.getElementById("contact-modal");
  if (contactModal) {
    const groomNameEl = contactModal.querySelector(
      ".contact-person:first-child .contact-name"
    );
    const groomPhoneEl = contactModal.querySelector(
      ".contact-person:first-child .call-btn"
    );
    const groomSmsEl = contactModal.querySelector(
      ".contact-person:first-child .sms-btn"
    );
    if (groomNameEl) groomNameEl.textContent = contacts.groom.name;
    if (groomPhoneEl)
      groomPhoneEl.href = `tel:${contacts.groom.phone.replace(/-/g, "")}`;
    if (groomSmsEl)
      groomSmsEl.href = `sms:${contacts.groom.phone.replace(/-/g, "")}`;

    const brideNameEl = contactModal.querySelector(
      ".contact-person:last-child .contact-name"
    );
    const bridePhoneEl = contactModal.querySelector(
      ".contact-person:last-child .call-btn"
    );
    const brideSmsEl = contactModal.querySelector(
      ".contact-person:last-child .sms-btn"
    );
    if (brideNameEl) brideNameEl.textContent = contacts.bride.name;
    if (bridePhoneEl)
      bridePhoneEl.href = `tel:${contacts.bride.phone.replace(/-/g, "")}`;
    if (brideSmsEl)
      brideSmsEl.href = `sms:${contacts.bride.phone.replace(/-/g, "")}`;
  }

  // 마무리 메시지
  if (messages.outro_message) {
    const outroEl = document.querySelector(".c-outro-text.center div");
    if (outroEl)
      outroEl.innerHTML = messages.outro_message.replace(/\n/g, "</br>");
  }

  // 마무리 이미지
  if (images.outro_photo) {
    const outroMediaEl = document.querySelector(".c-outro-inner");
    if (outroMediaEl) {
      const existingMedia = outroMediaEl.querySelector("img, video");
      if (!existingMedia) {
        const img = document.createElement("img");
        img.src = images.outro_photo;
        img.alt = "마무리";
        img.style.cssText = "width: 100%; height: auto;";
        outroMediaEl.insertBefore(img, outroMediaEl.firstChild);
      }
    }
  }

  // 갤러리 이미지 (이미 하드코딩되어 있으므로 필요시 동적으로 업데이트 가능)
  // 갤러리는 initGallery()에서 처리하므로 여기서는 생략

  // 배경음악 설정
  if (data.audio && data.audio.background_music) {
    window.backgroundMusicConfig = {
      url: data.audio.background_music,
      autoplay: data.audio.autoplay !== false, // 기본값 true
      loop: data.audio.loop !== false, // 기본값 true
      volume: data.audio.volume || 0.3, // 기본값 0.3
    };
    console.log("🎵 배경음악 설정:", window.backgroundMusicConfig);
  } else {
    console.log("🎵 배경음악 파일이 설정되지 않았습니다.");
  }
}

// 헬퍼 함수들
function updateTextContent(selector, text) {
  const el = document.querySelector(selector);
  if (el) el.textContent = text;
}

function updateMetaTag(property, content) {
  const selector = property.startsWith("og:")
    ? `meta[property="${property}"]`
    : `meta[name="${property}"]`;
  let meta = document.querySelector(selector);
  if (!meta) {
    meta = document.createElement("meta");
    if (property.startsWith("og:")) {
      meta.setAttribute("property", property);
    } else {
      meta.setAttribute("name", property);
    }
    document.head.appendChild(meta);
  }
  meta.setAttribute("content", content);
}

// 웹사이트 초기화
function initializeWebsite() {
  injectWeddingData(); // 데이터 주입을 가장 먼저 실행
  initFontLoading(); // 폰트 로딩 최적화 (iOS Safari)
  initImagePreloading(); // 이미지 프리로딩을 가장 먼저 실행
  initKakao(); // 카카오 SDK 초기화
  initCountdown();
  initGallery(); // 갤러리 초기화
  // initGuestbook();
  //   initRsvp();
  initFadeInAnimation(); // 페이드인 애니메이션 초기화
  initVideoAutoplay(); // 영상 자동 재생 초기화
  initAudio();
  initIntroVideo();
  initZoomPrevention(); // 확대 방지 초기화
  initZoomableMap(); // 지도 확대/축소 초기화
  showTab(0); // 기본 탭(식사안내) 표시
}

// 폰트 로딩 최적화 (iOS Safari 대응)
function initFontLoading() {
  console.log("🔤 폰트 로딩 최적화 시작...");

  // iOS Safari 감지
  const isIOS =
    /iPad|iPhone|iPod/.test(navigator.userAgent) && !window.MSStream;
  const isSafari = /^((?!chrome|android).)*safari/i.test(navigator.userAgent);

  if (isIOS || isSafari) {
    console.log("🍎 iOS Safari 감지 - 폰트 로딩 최적화 적용");

    // 폰트 로딩 확인
    const fonts = ["IropkeBatangM", "Pretendard Variable", "Noto Serif KR"];

    let fontsLoaded = 0;
    const totalFonts = fonts.length;

    fonts.forEach((fontName) => {
      if (document.fonts && document.fonts.check) {
        // Font Loading API 사용 (최신 브라우저)
        const fontCheck = `16px "${fontName}"`;

        if (document.fonts.check(fontCheck)) {
          fontsLoaded++;
          console.log(`✅ ${fontName} 폰트 로드 완료`);
        } else {
          // 폰트 로딩 대기
          document.fonts
            .load(fontCheck)
            .then(() => {
              fontsLoaded++;
              console.log(`✅ ${fontName} 폰트 지연 로드 완료`);
              checkAllFontsLoaded();
            })
            .catch((error) => {
              console.warn(`⚠️ ${fontName} 폰트 로드 실패:`, error);
              fontsLoaded++;
              checkAllFontsLoaded();
            });
        }
      } else {
        // 폴백: 타이머로 폰트 로딩 대기
        setTimeout(() => {
          fontsLoaded++;
          checkAllFontsLoaded();
        }, 1000);
      }
    });

    function checkAllFontsLoaded() {
      if (fontsLoaded >= totalFonts) {
        console.log("🎉 모든 폰트 로딩 완료");
        document.body.classList.add("fonts-loaded");

        // iOS에서 폰트 렌더링 강제 업데이트
        if (isIOS) {
          setTimeout(() => {
            document.body.style.fontFamily = document.body.style.fontFamily;
          }, 100);
        }
      }
    }

    // 초기 체크
    checkAllFontsLoaded();

    // 폰트 로딩 타임아웃 (3초)
    setTimeout(() => {
      if (fontsLoaded < totalFonts) {
        console.warn("⏰ 폰트 로딩 타임아웃 - 폴백 폰트 사용");
        document.body.classList.add("fonts-timeout");
      }
    }, 3000);
  }
}

// 이미지 프리로딩 초기화 (정적 페이지 버전)
function initImagePreloading() {
  console.log("🖼️ 이미지 프리로딩 시작...");

  // 정적 페이지에서는 페이지 이미지만 프리로딩
  const pageImageUrls = collectAllImageUrls();

  // wedding-data.js에서 갤러리 이미지 추가
  if (typeof weddingData !== "undefined" && weddingData.gallery_images) {
    weddingData.gallery_images.forEach((img) => {
      if (!pageImageUrls.includes(img)) {
        pageImageUrls.push(img);
      }
    });
  }

  // gallery_webp 폴더의 모든 이미지 추가
  const galleryWebpImages = [
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
  ];

  galleryWebpImages.forEach((img) => {
    if (!pageImageUrls.includes(img)) {
      pageImageUrls.push(img);
    }
  });

  if (pageImageUrls.length > 0) {
    totalImagesToPreload = pageImageUrls.length;
    console.log(`🚀 총 ${totalImagesToPreload}개 이미지 프리로딩 시작`);

    // 로딩 인디케이터 표시
    showLoadingIndicator();

    // 이미지 프리로딩 시작
    preloadImages(pageImageUrls);
  } else {
    console.log("프리로드할 이미지가 없습니다.");
  }
}

// 페이지의 모든 이미지 URL 수집
function collectAllImageUrls() {
  const imageUrls = new Set(); // 중복 제거를 위해 Set 사용

  // 1. background-image 스타일에서 이미지 URL 추출
  const elementsWithBgImage = document.querySelectorAll(
    '[style*="background-image"]'
  );
  elementsWithBgImage.forEach((element) => {
    const bgImage = element.style.backgroundImage;
    const urlMatch = bgImage.match(/url\(['"]?([^'"]+)['"]?\)/);
    if (urlMatch && urlMatch[1]) {
      imageUrls.add(urlMatch[1]);
    }
  });

  // 2. img 태그의 src 속성에서 이미지 URL 추출
  const imgElements = document.querySelectorAll("img");
  imgElements.forEach((img) => {
    if (img.src) {
      imageUrls.add(img.src);
    }
    // data-src 속성도 확인 (lazy loading용)
    if (img.dataset.src) {
      imageUrls.add(img.dataset.src);
    }
  });

  // 3. CSS에서 정의된 이미지들 (동적으로 추가될 수 있는 이미지들)
  const additionalImages = [
    // 메인 이미지들 (config에서 동적으로 로드되는 이미지들)
    // 이 부분은 서버에서 전달받아야 할 수도 있음
  ];

  additionalImages.forEach((url) => {
    if (url) imageUrls.add(url);
  });

  console.log(`🔍 발견된 이미지: ${imageUrls.size}개`, Array.from(imageUrls));
  return Array.from(imageUrls);
}

// 이미지들을 프리로드
function preloadImages(imageUrls) {
  let loadedCount = 0;

  imageUrls.forEach((url, index) => {
    const img = new Image();

    img.onload = function () {
      loadedCount++;
      preloadedImages.set(url, img);
      preloadingProgress = (loadedCount / totalImagesToPreload) * 100;

      console.log(
        `✅ 이미지 로드 완료 (${loadedCount}/${totalImagesToPreload}): ${url}`
      );
      updateLoadingProgress(preloadingProgress);

      // 모든 이미지 로드 완료
      if (loadedCount === totalImagesToPreload) {
        onAllImagesLoaded();
      }
    };

    img.onerror = function () {
      loadedCount++;
      console.warn(`❌ 이미지 로드 실패: ${url}`);
      updateLoadingProgress((loadedCount / totalImagesToPreload) * 100);

      // 실패해도 진행
      if (loadedCount === totalImagesToPreload) {
        onAllImagesLoaded();
      }
    };

    // 이미지 로딩 시작
    img.src = url;
  });
}

// 모든 이미지 로드 완료 시 호출
function onAllImagesLoaded() {
  console.log("🎉 모든 이미지 프리로딩 완료!");
  hideLoadingIndicator();

  // 갤러리 이미지 즉시 표시 (애니메이션 없음)
  applyPreloadedImages();

  // 프리로딩 완료를 전역 플래그로 설정
  window.imagesPreloaded = true;

  // 갤러리 애니메이션 비활성화 - 즉시 표시
  showGalleryImmediately();
}

// 프리로드된 이미지를 실제 요소에 적용
function applyPreloadedImages() {
  // 갤러리 이미지 즉시 표시
  const galleryItems = document.querySelectorAll(".gallery-grid .item");
  galleryItems.forEach((item) => {
    item.style.opacity = "1";
    item.classList.add("image-preloaded");
  });

  // 일반 img 태그들 즉시 표시
  const imgElements = document.querySelectorAll("img");
  imgElements.forEach((img) => {
    img.style.opacity = "1";
    img.classList.add("image-preloaded");
  });
}

// 로딩 인디케이터 표시
function showLoadingIndicator() {
  // 간단한 로딩 인디케이터를 페이지 상단에 표시
  const indicator = document.createElement("div");
  indicator.id = "image-loading-indicator";
  indicator.innerHTML = `
        <div style="
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 3px;
            background: rgba(234, 118, 100, 0.2);
            z-index: 9999;
        ">
            <div id="loading-progress" style="
                height: 100%;
                background: #ea7664;
                width: 0%;
                transition: width 0.3s ease;
            "></div>
        </div>
    `;
  document.body.appendChild(indicator);
}

// 로딩 진행률 업데이트
function updateLoadingProgress(progress) {
  const progressBar = document.getElementById("loading-progress");
  if (progressBar) {
    progressBar.style.width = progress + "%";
  }
}

// 로딩 인디케이터 숨기기
function hideLoadingIndicator() {
  const indicator = document.getElementById("image-loading-indicator");
  if (indicator) {
    // 부드럽게 사라지도록 애니메이션 추가
    indicator.style.opacity = "0";
    indicator.style.transition = "opacity 0.5s ease";
    setTimeout(() => {
      indicator.remove();
    }, 500);
  }
}

// 현재 화면에 보이는 요소들의 애니메이션 트리거
function triggerVisibleAnimations() {
  // 현재 뷰포트에 보이는 애니메이션 요소들 찾기
  const animationElements = document.querySelectorAll(
    ".fade-in, .fade-in-up, .fade-in-left, .fade-in-right, .fade-in-scale, .fade-in-spring"
  );

  animationElements.forEach((element) => {
    const rect = element.getBoundingClientRect();
    const isVisible = rect.top < window.innerHeight && rect.bottom > 0;

    if (isVisible && !element.classList.contains("animated")) {
      // 약간의 지연 후 애니메이션 클래스 추가
      setTimeout(() => {
        element.classList.add("animated");
        element.style.opacity = "1";
        element.style.transform = "translate(0px, 0px) scale(1)";
      }, 100);
    }
  });
}

// 영상 자동 재생 초기화
function initVideoAutoplay() {
  console.log("🎬 영상 자동 재생 초기화...");

  // Intersection Observer를 사용하여 뷰포트에 들어오는 영상 감지
  const videoObserver = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        const video = entry.target;

        if (entry.isIntersecting) {
          // 영상이 화면에 보이면 재생
          video.play().catch((error) => {
            console.warn("영상 자동 재생 실패:", error);
            // 자동 재생 실패 시 사용자 제스처 후 재생하도록 이벤트 리스너 추가
            video.addEventListener("click", () => {
              video.play();
            });
          });
        } else {
          // 영상이 화면에서 벗어나면 일시정지
          video.pause();
        }
      });
    },
    {
      threshold: 0.5, // 영상의 50%가 보일 때 트리거
      rootMargin: "50px", // 50px 여유를 두고 트리거
    }
  );

  // 모든 갤러리 영상에 Observer 적용
  const galleryVideos = document.querySelectorAll(".gallery-video");
  galleryVideos.forEach((video) => {
    videoObserver.observe(video);

    // 영상 설정
    video.muted = true; // 음소거 (자동 재생을 위해 필수)
    video.loop = true; // 반복 재생
    video.playsInline = true; // 모바일에서 전체화면 방지
    video.preload = "metadata"; // 메타데이터만 미리 로드

    // 영상 로드 완료 시 첫 프레임 표시
    video.addEventListener("loadeddata", () => {
      video.currentTime = 0;
    });

    // 영상 에러 처리
    video.addEventListener("error", (e) => {
      console.error("영상 로드 오류:", e);
      // 영상 로드 실패 시 대체 이미지나 처리 로직 추가 가능
    });
  });

  // 관리자 페이지의 갤러리 영상들도 처리
  const adminGalleryVideos = document.querySelectorAll(".gallery-item video");
  adminGalleryVideos.forEach((video) => {
    video.addEventListener("mouseenter", () => {
      video.play().catch((error) => {
        console.warn("관리자 영상 재생 실패:", error);
      });
    });

    video.addEventListener("mouseleave", () => {
      video.pause();
      video.currentTime = 0; // 처음으로 되감기
    });
  });
}

// 카운트다운 초기화
function initCountdown() {
  const weddingDate = new Date("2026-02-21 16:00:00");

  countdownInterval = setInterval(function () {
    const now = new Date();
    const timeLeft = weddingDate - now;

    if (timeLeft > 0) {
      const days = Math.floor(timeLeft / (1000 * 60 * 60 * 24));
      const hours = Math.floor(
        (timeLeft % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60)
      );
      const minutes = Math.floor((timeLeft % (1000 * 60 * 60)) / (1000 * 60));
      const seconds = Math.floor((timeLeft % (1000 * 60)) / 1000);

      updateCountdownDisplay(days, hours, minutes, seconds);
    } else {
      clearInterval(countdownInterval);
      updateCountdownDisplay(0, 0, 0, 0);
    }
  }, 1000);
}

// 카운트다운 디스플레이 업데이트
function updateCountdownDisplay(days, hours, minutes, seconds) {
  const countdown = document.getElementById("countdown");
  if (countdown) {
    countdown.innerHTML = `
            <div><span class="card">${days
              .toString()
              .padStart(2, "0")}</span><div class="desc">Days</div></div>
            <div><span>:</span></div>
            <div><span class="card">${hours
              .toString()
              .padStart(2, "0")}</span><div class="desc">Hour</div></div>
            <div><span>:</span></div>
            <div><span class="card">${minutes
              .toString()
              .padStart(2, "0")}</span><div class="desc">Min</div></div>
            <div><span>:</span></div>
            <div><span class="card">${seconds
              .toString()
              .padStart(2, "0")}</span><div class="desc">Sec</div></div>
        `;
  }

  // D-Day 텍스트 업데이트
  const ddayText = document.getElementById("dday-text");
  if (ddayText && days > 0) {
    ddayText.innerHTML = `
            <span>혁재 <span style="color:#ea7664">♥</span> 진주의 결혼식이 </span>
            <span><span style="color:#ea7664">${days}일</span> <span>남았습니다.</span></span>
        `;
  } else if (ddayText && days === 0) {
    ddayText.innerHTML = `
            <span>혁재 <span style="color:#ea7664">♥</span> 진주의 결혼식이 </span>
            <span><span style="color:#ea7664">오늘</span> <span>입니다!</span></span>
        `;
  }
}

// 갤러리 초기화
function initGallery() {
  console.log("🖼️ 갤러리 초기화 시작...");

  const galleryGrid = document.getElementById("gallery-grid");
  if (!galleryGrid) {
    console.warn("⚠️ 갤러리 그리드를 찾을 수 없습니다.");
    return;
  }

  // gallery_webp 폴더의 모든 이미지 파일 목록
  const galleryImages = [
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
  ];

  console.log(`🖼️ ${galleryImages.length}개의 갤러리 이미지 발견`);

  // 기존 갤러리 아이템 제거
  galleryGrid.innerHTML = "";

  // 각 이미지의 비율과 위치 정보를 저장할 배열
  const imageData = [];
  let loadedCount = 0;
  let errorCount = 0;

  // 모든 이미지 로드 및 비율 확인
  galleryImages.forEach((imagePath, index) => {
    const img = new Image();

    img.onload = function () {
      loadedCount++;
      const aspectRatio = img.width / img.height;

      // 비율에 따라 grid span 결정
      // 세로형 (aspectRatio < 1): span 2 (높이 2칸)
      // 가로형 (aspectRatio >= 1): span 1 (높이 1칸)
      const rowSpan = aspectRatio < 1 ? 2 : 1;

      imageData.push({
        path: imagePath,
        index: index,
        aspectRatio: aspectRatio,
        rowSpan: rowSpan,
        width: img.width,
        height: img.height,
      });

      console.log(
        `✅ 이미지 로드 성공 (${loadedCount}/${
          galleryImages.length
        }): ${imagePath} - 비율: ${aspectRatio.toFixed(2)}, span: ${rowSpan}`
      );

      // 모든 이미지 로드 완료 시 grid 배치
      if (loadedCount + errorCount === galleryImages.length) {
        console.log(
          `📊 이미지 로드 완료: 성공 ${loadedCount}, 실패 ${errorCount}, 총 ${imageData.length}개`
        );
        if (imageData.length > 0) {
          arrangeGalleryGrid(imageData);
        } else {
          console.error("❌ 로드된 이미지가 없습니다.");
        }
      }
    };

    img.onerror = function () {
      errorCount++;
      console.error(`❌ 이미지 로드 실패 (${errorCount}): ${imagePath}`);

      // 모든 이미지 처리 완료 시 grid 배치
      if (loadedCount + errorCount === galleryImages.length) {
        console.log(
          `📊 이미지 로드 완료: 성공 ${loadedCount}, 실패 ${errorCount}, 총 ${imageData.length}개`
        );
        if (imageData.length > 0) {
          arrangeGalleryGrid(imageData);
        } else {
          console.error("❌ 로드된 이미지가 없습니다.");
        }
      }
    };

    // 이미지 로드 시작
    img.src = imagePath;
  });

  // 타임아웃 설정 (10초 후에도 로드되지 않으면 강제로 배치)
  setTimeout(() => {
    if (imageData.length > 0 && galleryGrid.children.length === 0) {
      console.warn(
        "⏰ 타임아웃: 일부 이미지가 로드되지 않았지만 배치를 시작합니다."
      );
      arrangeGalleryGrid(imageData);
    }
  }, 10000);
}

// 갤러리 그리드 배치 함수
function arrangeGalleryGrid(imageData) {
  const galleryGrid = document.getElementById("gallery-grid");
  if (!galleryGrid) return;

  console.log("📐 갤러리 그리드 배치 시작...", imageData);

  // 이미지를 인덱스 순서대로 정렬
  imageData.sort((a, b) => a.index - b.index);

  // 2열 그리드에서 각 열의 현재 높이 추적
  let col1Height = 0;
  let col2Height = 0;
  let currentRow = 1; // 현재 행 위치

  imageData.forEach((data, index) => {
    const gridItem = document.createElement("div");
    const delayClass = `fade-in-delay-${(index % 3) + 1}`;
    gridItem.className = `grid-item fade-in-up ${delayClass}`;

    // 비율에 따라 grid-row와 grid-column 결정
    const rowSpan = data.rowSpan;
    let gridRowStart, gridColumnStart, gridColumnEnd;

    // 높이가 낮은 열에 배치
    if (col1Height <= col2Height) {
      // 첫 번째 열에 배치
      gridRowStart = col1Height + 1;
      gridColumnStart = 1;
      gridColumnEnd = 2;
      col1Height += rowSpan;
    } else {
      // 두 번째 열에 배치
      gridRowStart = col2Height + 1;
      gridColumnStart = 2;
      gridColumnEnd = 3;
      col2Height += rowSpan;
    }

    gridItem.style.gridRow = `${gridRowStart} / span ${rowSpan}`;
    gridItem.style.gridColumn = `${gridColumnStart} / ${gridColumnEnd}`;

    // 내부 item 요소 생성
    const item = document.createElement("div");
    item.className = "item image-preloaded";
    item.style.cssText = `
      background-image: url('${data.path}');
      background-size: cover;
      background-position: center;
      background-repeat: no-repeat;
      aspect-ratio: ${data.width} / ${data.height};
      width: 100%;
      height: 100%;
      display: block;
      cursor: pointer;
    `;
    item.onclick = function () {
      openImageModal(data.path);
    };

    gridItem.appendChild(item);
    galleryGrid.appendChild(gridItem);

    console.log(
      `📐 이미지 ${index + 1} 배치: ${
        data.path
      } - grid-row: ${gridRowStart} / span ${rowSpan}, grid-column: ${gridColumnStart} / ${gridColumnEnd}, 비율: ${data.aspectRatio.toFixed(
        2
      )}`
    );
  });

  console.log("✅ 갤러리 그리드 배치 완료");

  // 갤러리 요소들이 생성된 후 IntersectionObserver에 등록
  setTimeout(() => {
    const galleryFadeElements = galleryGrid.querySelectorAll(
      ".grid-item.fade-in-up"
    );
    galleryFadeElements.forEach((el) => {
      // 이미 화면에 보이는 요소는 즉시 애니메이션
      const rect = el.getBoundingClientRect();
      const isVisible = rect.top < window.innerHeight && rect.bottom > 0;

      if (isVisible) {
        el.classList.add("animated");
      } else {
        // 옵저버에 등록
        const observer = new IntersectionObserver(
          (entries) => {
            entries.forEach((entry) => {
              if (entry.isIntersecting) {
                entry.target.classList.add("animated");
                observer.unobserve(entry.target);
              }
            });
          },
          {
            threshold: 0.1,
            rootMargin: "50px",
          }
        );
        observer.observe(el);
      }
    });
  }, 100);
}

// 방명록 초기화
function initGuestbook() {
  loadGuestbook();
}

// 참석 의사 전달 초기화
function initRsvp() {
  const form = document.getElementById("rsvp-form");
  if (!form) {
    return;
  }

  const feedback = document.getElementById("rsvp-feedback");
  const submitBtn = form.querySelector(".rsvp-submit-btn");

  form.addEventListener("submit", function (event) {
    event.preventDefault();

    if (submitBtn) {
      submitBtn.disabled = true;
      submitBtn.textContent = "전송 중...";
    }

    if (feedback) {
      feedback.style.display = "none";
      feedback.classList.remove("success", "error");
      feedback.textContent = "";
    }

    const side =
      (form.querySelector('input[name="rsvp_side"]:checked') || {}).value ||
      "groom";
    const name = (form.querySelector("#rsvp-name") || {}).value.trim();
    const attendeesValue = (form.querySelector("#rsvp-attendees") || {}).value;
    const attendees = Math.max(1, parseInt(attendeesValue, 10) || 1);
    const companion = (
      form.querySelector("#rsvp-companion") || {}
    ).value.trim();
    const meal =
      (form.querySelector('input[name="rsvp_meal"]:checked') || {}).value ||
      "planned";

    if (!name) {
      showRsvpFeedback("성함을 입력해주세요.", false);
      if (submitBtn) {
        submitBtn.disabled = false;
        submitBtn.textContent = "참석 의사 전달하기";
      }
      return;
    }

    // 정적 페이지에서는 서버 API가 없으므로 연락처 정보를 표시
    const contacts =
      typeof weddingData !== "undefined" ? weddingData.contacts : null;
    let contactInfo = "";

    if (side === "groom" && contacts && contacts.groom) {
      contactInfo = `신랑측: ${contacts.groom.name} (${contacts.groom.phone})`;
    } else if (side === "bride" && contacts && contacts.bride) {
      contactInfo = `신부측: ${contacts.bride.name} (${contacts.bride.phone})`;
    }

    const message = `정적 페이지에서는 참석 의사를 자동으로 전달할 수 없습니다.\n\n${
      contactInfo
        ? contactInfo + "로 직접 연락 부탁드립니다."
        : "연락처로 직접 연락 부탁드립니다."
    }\n\n입력하신 정보:\n- 성함: ${name}\n- 참석 인원: ${attendees}명${
      companion ? "\n- 동행인: " + companion : ""
    }\n- 식사 여부: ${
      meal === "planned" ? "예정" : meal === "not_planned" ? "미예정" : "미정"
    }`;

    showRsvpFeedback(message, false);

    if (submitBtn) {
      submitBtn.disabled = false;
      submitBtn.textContent = "참석 의사 전달하기";
    }

    // 5초 후 모달 닫기
    setTimeout(() => {
      closeRsvpModal();
    }, 5000);
  });

  function showRsvpFeedback(message, isSuccess) {
    if (!feedback) {
      alert(message);
      return;
    }

    feedback.textContent = message;
    feedback.classList.remove("success", "error");
    feedback.classList.add(isSuccess ? "success" : "error");
    feedback.style.display = "block";
  }
}

// 방명록 로드 (정적 페이지 버전)
function loadGuestbook() {
  // 정적 페이지에서는 서버가 없으므로 빈 방명록 표시
  const guestbookComments = document.getElementById("guestbook-comments");
  if (guestbookComments) {
    guestbookComments.innerHTML = `
            <div class="empty-message" style="text-align: center; padding: 40px; color: #999;">
                정적 페이지에서는 방명록 기능을 사용할 수 없습니다.<br>
                연락처로 직접 축하 메시지를 전달해주세요! 💝
            </div>
        `;
  }
}

// 방명록 표시
function displayGuestbook(comments) {
  const guestbookComments = document.getElementById("guestbook-comments");
  if (!guestbookComments) return;

  guestbookComments.innerHTML = "";

  if (comments.length === 0) {
    guestbookComments.innerHTML = `
            <div class="empty-message" style="text-align: center; padding: 40px; color: #999;">
                아직 작성된 방명록이 없습니다.<br>
                첫 번째 축하 메시지를 남겨보세요! 💝
            </div>
        `;
    return;
  }

  comments.forEach((comment) => {
    const item = document.createElement("div");
    item.className = "item white";
    item.innerHTML = `
            <div class="close">
                <span class="date">${comment.date}</span>
                <span class="icon" onclick="deleteGuestbookEntry(${comment.id})" title="삭제">
                    <svg width="15px" height="15px" viewBox="0 0 15 15" fill="black" xmlns="http://www.w3.org/2000/svg">
                        <path fill-rule="evenodd" clip-rule="evenodd" d="M6.7929 7.49998L1.14645 1.85353L1.85356 1.14642L7.50001 6.79287L13.1465 1.14642L13.8536 1.85353L8.20711 7.49998L13.8536 13.1464L13.1465 13.8535L7.50001 8.20708L1.85356 13.8535L1.14645 13.1464L6.7929 7.49998Z"></path>
                    </svg>
                </span>
            </div>
            <div class="name">${comment.name}</div>
            <div class="text">${comment.message}</div>
        `;
    guestbookComments.appendChild(item);
  });
}

// 페이드인 애니메이션 초기화
function initFadeInAnimation() {
  const observerOptions = {
    threshold: 0.15,
    rootMargin: "0px 0px -80px 0px",
  };

  const observer = new IntersectionObserver(function (entries) {
    entries.forEach((entry) => {
      if (entry.isIntersecting) {
        const element = entry.target;

        // animated 클래스 추가로 CSS transition 트리거
        if (!element.classList.contains("animated")) {
          element.classList.add("animated");
        }
      }
    });
  }, observerOptions);

  // 모든 fade-in 요소 초기화 및 인라인 스타일 제거
  const fadeInSelectors = [
    ".fade-in",
    ".fade-in-up",
    ".fade-in-left",
    ".fade-in-right",
    ".fade-in-scale",
    ".fade-in-spring",
  ];

  fadeInSelectors.forEach((selector) => {
    document.querySelectorAll(selector).forEach((el) => {
      // 갤러리 관련 요소의 인라인 스타일 제거
      if (
        el.closest(".gallery-container") ||
        el.closest(".gallery-grid") ||
        el.classList.contains("gallery-container") ||
        el.classList.contains("grid-item")
      ) {
        el.style.removeProperty("opacity");
        el.style.removeProperty("transform");
      }
      observer.observe(el);
    });
  });

  // 페이지 로드 시 이미 화면에 보이는 요소들 즉시 애니메이션
  setTimeout(() => {
    const allFadeElements = document.querySelectorAll(
      ".fade-in, .fade-in-up, .fade-in-left, .fade-in-right, .fade-in-scale, .fade-in-spring"
    );
    allFadeElements.forEach((el) => {
      const rect = el.getBoundingClientRect();
      const isVisible = rect.top < window.innerHeight && rect.bottom > 0;

      if (isVisible && !el.classList.contains("animated")) {
        el.classList.add("animated");
      }
    });
  }, 100);
}

// 오디오 초기화
function initAudio() {
  const audioPlayer = document.getElementById("bgm-player");
  const audioAlert = document.querySelector(".audio-alert");

  if (audioPlayer && audioAlert) {
    console.log("🎵 배경음악 초기화");

    // 관리자 설정에서 배경음악 설정 적용
    if (window.backgroundMusicConfig) {
      const config = window.backgroundMusicConfig;

      // 오디오 소스 설정
      audioPlayer.innerHTML = `<source src="${config.url}" type="audio/mpeg">`;
      audioPlayer.load(); // 새 소스 로드

      // 설정 적용
      audioPlayer.loop = config.loop;
      audioPlayer.volume = config.volume;

      // muted 상태 해제 (자동재생을 위해 일시적으로 muted로 시작)
      if (config.autoplay) {
        audioPlayer.muted = false;
      }

      console.log("🎵 배경음악 설정 적용:", config);

      // 자동 재생 설정이 있으면 적극적으로 재생 시도
      if (config.autoplay) {
        console.log("🎵 자동재생 설정 감지됨");

        // 여러 시점에서 자동재생 시도하는 함수
        const tryAutoplay = () => {
          if (audioPlayer.paused) {
            audioPlayer
              .play()
              .then(() => {
                console.log("🎵 배경음악 자동 재생 성공");
                audioAlert.classList.add("playing");
              })
              .catch((e) => {
                console.log("자동 재생 실패:", e);
              });
          }
        };

        // 1. 즉시 재생 시도
        setTimeout(tryAutoplay, 100);

        // 2. 페이지 로드 완료 후 재생 시도
        if (document.readyState === "complete") {
          setTimeout(tryAutoplay, 500);
        } else {
          window.addEventListener("load", () => {
            setTimeout(tryAutoplay, 500);
          });
        }

        // 3. 사용자의 첫 번째 상호작용 시 재생 (모든 이벤트 타입에 대해)
        const userInteractionEvents = [
          "click",
          "touchstart",
          "touchend",
          "mousedown",
          "keydown",
        ];
        const handleFirstInteraction = () => {
          console.log("🎵 사용자 상호작용 감지됨");
          tryAutoplay();
          // 모든 이벤트 리스너 제거
          userInteractionEvents.forEach((event) => {
            document.removeEventListener(event, handleFirstInteraction, true);
          });
        };

        userInteractionEvents.forEach((event) => {
          document.addEventListener(event, handleFirstInteraction, {
            once: true,
            capture: true,
          });
        });

        // 4. 스크롤 시에도 재생 시도 (모바일에서 유용)
        let scrollTried = false;
        const handleScroll = () => {
          if (!scrollTried) {
            scrollTried = true;
            console.log("🎵 스크롤 감지됨");
            tryAutoplay();
            window.removeEventListener("scroll", handleScroll);
          }
        };
        window.addEventListener("scroll", handleScroll, { once: true });
      }
    } else {
      // 기본 설정
      audioPlayer.volume = 0.3;
    }

    // 오디오 알림 버튼 클릭 이벤트
    audioAlert.addEventListener("click", function () {
      if (audioPlayer.paused) {
        audioPlayer
          .play()
          .then(() => {
            console.log("🎵 배경음악 재생");
            audioAlert.classList.add("playing");
          })
          .catch((e) => {
            console.error("배경음악 재생 실패:", e);
            alert("음악을 재생하려면 브라우저에서 오디오를 허용해주세요.");
          });
      } else {
        audioPlayer.pause();
        console.log("🎵 배경음악 일시정지");
        audioAlert.classList.remove("playing");
      }
    });

    // 음악 재생/일시정지 이벤트
    audioPlayer.addEventListener("play", function () {
      audioAlert.classList.add("playing");
    });

    audioPlayer.addEventListener("pause", function () {
      audioAlert.classList.remove("playing");
    });

    // 오디오 로드 완료 시
    audioPlayer.addEventListener("loadeddata", function () {
      console.log("🎵 배경음악 로드 완료");

      // 자동재생 설정이 있고 아직 재생되지 않았다면 재생 시도
      if (
        window.backgroundMusicConfig &&
        window.backgroundMusicConfig.autoplay &&
        audioPlayer.paused
      ) {
        // 로드 완료 후 약간의 딜레이를 두고 재생 시도
        setTimeout(() => {
          audioPlayer
            .play()
            .then(() => {
              console.log("🎵 배경음악 로드 완료 후 자동 재생 시작");
              audioAlert.classList.add("playing");
            })
            .catch((e) => {
              console.log("로드 완료 후 자동 재생 실패:", e);
            });
        }, 200);
      }
    });

    // canplaythrough 이벤트에서도 자동재생 시도 (더 안정적)
    audioPlayer.addEventListener("canplaythrough", function () {
      console.log("🎵 배경음악 완전히 로드됨");

      if (
        window.backgroundMusicConfig &&
        window.backgroundMusicConfig.autoplay &&
        audioPlayer.paused
      ) {
        setTimeout(() => {
          audioPlayer
            .play()
            .then(() => {
              console.log("🎵 배경음악 완전 로드 후 자동 재생 시작");
              audioAlert.classList.add("playing");
            })
            .catch((e) => {
              console.log("완전 로드 후 자동 재생 실패:", e);
            });
        }, 300);
      }
    });
  }
}

// 기존 함수들 제거됨 - 단순화된 오디오 시스템 사용

// 인트로 비디오 초기화 (꽃가루 효과)
function initIntroVideo() {
  const introPlayer = document.getElementById("intro-player");

  if (introPlayer) {
    // 비디오 로드 및 재생
    introPlayer.addEventListener("canplaythrough", function () {
      introPlayer
        .play()
        .catch((e) => console.log("Intro video play failed:", e));
    });

    // 비디오 스타일 설정
    introPlayer.style.width = "100%";
    introPlayer.style.opacity = "1";
    introPlayer.style.visibility = "initial";
  }
}

// 탭 표시 함수
function showTab(index) {
  const titles = document.querySelectorAll(".ntab .title");
  const contents = document.querySelectorAll(".ntab .content.ntab-panel");

  // 모든 탭 비활성화
  titles.forEach((title) => title.classList.remove("active"));
  contents.forEach((content) => content.classList.remove("active"));

  // 선택된 탭 활성화
  if (titles[index]) titles[index].classList.add("active");
  if (contents[index]) contents[index].classList.add("active");

  // 탭 내용 업데이트
  const tabContent = document.getElementById("tab-content");
  if (tabContent) {
    let content = "";
    switch (index) {
      case 0: // 식사안내
        content = `
                    <div class="content ntab-panel active">
                        <div class="text">
                        예식 후 식사를 준비하였습니다.<br>
                        맛있는 식사와 함께<br>
                        즐거운 시간 보내시기 바랍니다.<br><br>
                        • 위치: 건물 내 연회장<br>
                        • 식사 시간: 15:15 ~ 17:45<br>
                        • 만 6세 미만 유아는 식권 없이 식사 가능합니다.<br>
                        </div>
                    </div>
                `;
        break;
      case 1: // 주차안내
        content = `
                    <div class="content ntab-panel active">
                        <div class="text">
                        컨벤션 지하주차장을 이용해주세요.<br>
                        • 하객 무료주차: 2시간<br>
                        • 초과 30분당 1,500원<br><br>
                        
                        만차시, 맞은편 전쟁기념관에<br>
                        주차 안내를 해드리고 있습니다.<br><br>
                        • 주차할인: 안내문 제출 및 차량등록 필수<br>
                        • 등록 위치: 컨벤션 안내데스크<br>
                        • 안내문 위치: 컨벤션 주차장 입구<br>
                        • 만차시에만 주차 할인 가능<br><br>

                        대중교통 이용을 권장드립니다.
                        </div>
                    </div>
                `;
        break;
    }
    tabContent.innerHTML = content;
  }
}

// 계좌 정보 토글
function toggleAccount(element) {
  const item = element.closest(".item");
  const texts = item.querySelectorAll(".text");
  const arrow = element.querySelector(".arrow");
  const title = element;

  const isExpanded = title.classList.contains("expand");

  if (isExpanded) {
    // 접기
    title.classList.remove("expand");
    arrow.classList.remove("rotate");
    texts.forEach((text) => {
      text.style.height = "0px";
      text.style.display = "none";
    });
  } else {
    // 펼치기
    title.classList.add("expand");
    arrow.classList.add("rotate");
    texts.forEach((text) => {
      text.style.display = "block";
      text.style.height = "auto";
    });
  }
}

// 계좌번호 복사
function copyAccount(accountInfo) {
  navigator.clipboard
    .writeText(accountInfo)
    .then(function () {
      alert("계좌번호가 복사되었습니다.");
    })
    .catch(function (err) {
      console.error("복사 실패:", err);
      alert("복사에 실패했습니다.");
    });
}

// 연락처 모달 표시
function showContactModal() {
  const modal = document.getElementById("contact-modal");
  if (modal) {
    modal.style.display = "flex";
    document.body.style.overflow = "hidden";

    // 애니메이션을 위해 약간의 딜레이 후 active 클래스 추가
    setTimeout(() => {
      modal.classList.add("active");
    }, 10);
  }
}

function closeContactModal(event) {
  // event가 있고 클릭된 요소가 오버레이가 아니라면 무시
  if (event && event.target !== event.currentTarget) {
    return;
  }

  const modal = document.getElementById("contact-modal");
  if (modal) {
    modal.classList.remove("active");

    // 애니메이션 완료 후 숨김
    setTimeout(() => {
      modal.style.display = "none";
      document.body.style.overflow = "auto";
    }, 300);
  }
}

// RSVP 모달 표시
function showRsvpModal() {
  const modal = document.getElementById("rsvp-modal");
  if (!modal) {
    alert("참석 의사 전달 기능이 준비되지 않았습니다.");
    return;
  }

  resetRsvpForm();
  modal.style.display = "flex";
  document.body.style.overflow = "hidden";

  setTimeout(() => {
    modal.classList.add("active");
    const container = modal.querySelector(".rsvp-modal-content");
    if (container) {
      container.scrollTop = 0;
    }
  }, 10);
}

function closeRsvpModal(event) {
  if (event && event.target && event.target !== event.currentTarget) {
    return;
  }

  const modal = document.getElementById("rsvp-modal");
  if (!modal) {
    return;
  }

  modal.classList.remove("active");

  setTimeout(() => {
    modal.style.display = "none";
    document.body.style.overflow = "auto";
  }, 300);
}

function resetRsvpForm() {
  const form = document.getElementById("rsvp-form");
  const feedback = document.getElementById("rsvp-feedback");

  if (form) {
    form.reset();
    const attendeesInput = form.querySelector("#rsvp-attendees");
    if (attendeesInput) {
      attendeesInput.value = "1";
    }
    const submitBtn = form.querySelector(".rsvp-submit-btn");
    if (submitBtn) {
      submitBtn.disabled = false;
      submitBtn.textContent = "참석 의사 전달하기";
    }
  }

  if (feedback) {
    feedback.style.display = "none";
    feedback.classList.remove("success", "error");
    feedback.textContent = "";
  }
}

// 방명록 모달 표시
function showGuestbookModal() {
  const modal = document.getElementById("guestbook-modal");
  if (modal) {
    modal.style.display = "block";
    document.body.style.overflow = "hidden";
  }
}

function closeGuestbookModal() {
  const modal = document.getElementById("guestbook-modal");
  if (modal) {
    modal.style.display = "none";
    document.body.style.overflow = "auto";
    // 폼 초기화
    document.getElementById("guestbook-form").reset();
  }
}

function submitGuestbook() {
  const name = document.getElementById("guestbook-name").value.trim();
  const message = document.getElementById("guestbook-message").value.trim();
  const password = document.getElementById("guestbook-password").value.trim();

  if (!name) {
    alert("이름을 입력해주세요.");
    return;
  }

  if (!message) {
    alert("메시지를 입력해주세요.");
    return;
  }

  if (!password) {
    alert("비밀번호를 입력해주세요.");
    return;
  }

  // 정적 페이지에서는 서버가 없으므로 경고 메시지 표시
  alert(
    "정적 페이지에서는 방명록을 저장할 수 없습니다.\n\n연락처로 직접 축하 메시지를 전달해주세요!"
  );
  closeGuestbookModal();
}

function deleteGuestbookEntry(entryId) {
  // 정적 페이지에서는 방명록 삭제 기능 없음
  alert("정적 페이지에서는 방명록 삭제 기능을 사용할 수 없습니다.");
}

// 화환 보내기 링크 이동
function showFlowerModal() {
  const flowerUrl = "https://w.theirmood.com/garland/X0vpRQ6E3E";
  window.open(flowerUrl, "_blank", "noopener,noreferrer");
}

// 이미지 모달 열기 (갤러리 스와이프 모달)
function openImageModal(imageSrc) {
  // 모든 갤러리 이미지 수집
  const galleryItems = document.querySelectorAll(".gallery-grid .item");
  const galleryImages = [];

  galleryItems.forEach((item) => {
    const bgImage = item.style.backgroundImage;
    const urlMatch = bgImage.match(/url\(['"]?([^'"]+)['"]?\)/);
    if (urlMatch && urlMatch[1]) {
      galleryImages.push(urlMatch[1]);
    }
  });
  console.log("galleryItems", galleryItems);

  if (galleryImages.length === 0) return;

  // 현재 이미지의 인덱스 찾기
  const currentIndex = galleryImages.indexOf(imageSrc);
  let currentImageIndex = currentIndex >= 0 ? currentIndex : 0;

  // 갤러리 스와이프 모달 생성
  console.log("갤러리 스와이프 모달 생성");
  const modal = document.createElement("div");
  modal.className = "modal-mask gallery-swipe-modal";
  modal.innerHTML = `
        <div class="gallery-modal-wrapper">
            <div class="gallery-modal-container">
                <div class="gallery-modal-images" id="gallery-modal-images">
                    ${galleryImages
                      .map(
                        (src, index) => `
                        <div class="gallery-modal-item ${
                          index === currentImageIndex ? "active" : ""
                        }" data-index="${index}">
                            <img src="${src}" alt="갤러리 이미지 ${index + 1}">
                        </div>
                    `
                      )
                      .join("")}
                </div>
                
                <!-- 네비게이션 버튼 -->
                <div class="gallery-modal-nav">
                    <button class="gallery-nav-btn prev-btn" onclick="navigateGallery(-1)">
                        <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                            <path d="M15 18L9 12L15 6" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                        </svg>
                    </button>
                    <button class="gallery-nav-btn next-btn" onclick="navigateGallery(1)">
                        <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                            <path d="M9 18L15 12L9 6" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                        </svg>
                    </button>
                </div>
                
                <!-- 인디케이터 -->
                <div class="gallery-modal-indicator">
                    ${galleryImages
                      .map(
                        (_, index) => `
                        <span class="gallery-modal-dot ${
                          index === currentImageIndex ? "active" : ""
                        }" data-index="${index}"></span>
                    `
                      )
                      .join("")}
                </div>
                
                <!-- 닫기 버튼 -->
                <button class="gallery-modal-close" onclick="closeGalleryModal()">
                    <svg viewBox="0 0 15 15" fill="white" xmlns="http://www.w3.org/2000/svg">
                        <path d="M6.7929 7.49998L1.14645 1.85353L1.85356 1.14642L7.50001 6.79287L13.1465 1.14642L13.8536 1.85353L8.20711 7.49998L13.8536 13.1464L13.1465 13.8535L7.50001 8.20708L1.85356 13.8535L1.14645 13.1464L6.7929 7.49998Z"></path>
                    </svg>
                </button>
            </div>
        </div>
    `;

  // 모달 전체 영역 클릭 시 닫기
  modal.addEventListener("click", function (e) {
    if (e.target === modal) {
      closeGalleryModal();
    }
  });

  // 현재 스크롤 위치 저장
  const scrollY = window.scrollY;
  document.body.style.top = `-${scrollY}px`;

  document.body.appendChild(modal);
  document.body.classList.add("modal-open");

  // 스와이프 기능 초기화
  initGalleryModalSwipe(currentImageIndex, galleryImages.length);
}

// 갤러리 모달 네비게이션
function navigateGallery(direction) {
  const modal = document.querySelector(".gallery-swipe-modal");
  if (!modal) return;

  const items = modal.querySelectorAll(".gallery-modal-item");
  const dots = modal.querySelectorAll(".gallery-modal-dot");
  const currentActive = modal.querySelector(".gallery-modal-item.active");

  if (!currentActive) return;

  const currentIndex = parseInt(currentActive.dataset.index);
  const totalItems = items.length;

  let newIndex = currentIndex + direction;

  // 순환 네비게이션
  if (newIndex < 0) newIndex = totalItems - 1;
  if (newIndex >= totalItems) newIndex = 0;

  // 현재 활성 아이템 비활성화
  currentActive.classList.remove("active");
  dots[currentIndex].classList.remove("active");

  // 새 아이템 활성화
  items[newIndex].classList.add("active");
  dots[newIndex].classList.add("active");
}

// 갤러리 모달 스와이프 기능 초기화
function initGalleryModalSwipe(currentIndex, totalImages) {
  const modal = document.querySelector(".gallery-swipe-modal");
  if (!modal) return;

  let startX = 0;
  let startY = 0;
  let isScrolling = false;

  modal.addEventListener("touchstart", handleModalTouchStart, {
    passive: true,
  });
  modal.addEventListener("touchmove", handleModalTouchMove, { passive: true });
  modal.addEventListener("touchend", handleModalTouchEnd, { passive: true });

  function handleModalTouchStart(e) {
    startX = e.touches[0].clientX;
    startY = e.touches[0].clientY;
    isScrolling = false;
  }

  function handleModalTouchMove(e) {
    if (!startX || !startY) return;

    const currentX = e.touches[0].clientX;
    const currentY = e.touches[0].clientY;

    const diffX = Math.abs(currentX - startX);
    const diffY = Math.abs(currentY - startY);

    // 수평 스크롤이 수직 스크롤보다 크면 스와이프로 인식
    if (diffX > diffY) {
      isScrolling = true;
    }
  }

  function handleModalTouchEnd(e) {
    if (!isScrolling) return;

    const endX = e.changedTouches[0].clientX;
    const diffX = startX - endX;

    // 스와이프 거리가 충분하면 다음/이전 이미지로 이동
    if (Math.abs(diffX) > 50) {
      if (diffX > 0) {
        // 왼쪽으로 스와이프 - 다음 이미지
        navigateGallery(1);
      } else {
        // 오른쪽으로 스와이프 - 이전 이미지
        navigateGallery(-1);
      }
    }

    startX = 0;
    startY = 0;
    isScrolling = false;
  }
}

// 갤러리 모달 닫기 함수
function closeGalleryModal(element) {
  const modal = element
    ? element.closest(".modal-mask")
    : document.querySelector(
        ".modal-mask.gallery, .modal-mask.gallery-swipe-modal"
      );
  if (modal) {
    // 스크롤 위치 복원
    const scrollY = document.body.style.top;
    document.body.style.position = "";
    document.body.style.top = "";
    document.body.style.width = "";
    document.body.style.height = "";
    document.body.style.left = "";
    document.body.classList.remove("modal-open");

    if (scrollY) {
      window.scrollTo(0, parseInt(scrollY || "0") * -1);
    }

    modal.remove();
  }
}

// 모달 닫기
function closeModal(modalId) {
  const modal = document.getElementById(modalId);
  if (modal) {
    modal.style.display = "none";
    document.body.classList.remove("modal-open");
  }
}

// 네이버 지도 열기
function openNaverMap() {
  const address = "서울특별시 영등포구 문래동3가 55-16";
  const placeName = "JK아트컨벤션";
  const searchQuery = `${placeName} ${address}`;
  const url = `https://map.naver.com/v5/search/${encodeURIComponent(
    searchQuery
  )}`;
  window.open(url, "_blank");
}

// 카카오 내비 열기
function openKakaoNavi() {
  const address = "서울특별시 영등포구 문래동3가 55-16";

  // 모바일에서 카카오내비 앱 실행 시도
  if (
    /Android|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(
      navigator.userAgent
    )
  ) {
    const kakaoNaviUrl = `kakaomap://search?q=${encodeURIComponent(address)}`;
    const fallbackUrl = `https://map.kakao.com/link/search/${encodeURIComponent(
      address
    )}`;

    // 앱 실행 시도
    window.location.href = kakaoNaviUrl;

    // 앱이 설치되지 않은 경우 웹으로 이동
    setTimeout(() => {
      window.open(fallbackUrl, "_blank");
    }, 2000);
  } else {
    // 데스크톱에서는 카카오맵 웹으로 이동
    const webUrl = `https://map.kakao.com/link/search/${encodeURIComponent(
      address
    )}`;
    window.open(webUrl, "_blank");
  }
}

// 티맵 열기
function openTmap() {
  const address = "서울특별시 영등포구 문래동3가 55-16";
  const placeName = "JK아트컨벤션";

  // 모바일에서 티맵 앱 실행 시도
  if (
    /Android|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(
      navigator.userAgent
    )
  ) {
    const tmapUrl = `tmap://search?name=${encodeURIComponent(
      placeName
    )}&address=${encodeURIComponent(address)}`;
    const fallbackUrl = `https://tmap.life/route/search?name=${encodeURIComponent(
      placeName + " " + address
    )}`;

    // 앱 실행 시도
    window.location.href = tmapUrl;

    // 앱이 설치되지 않은 경우 웹으로 이동
    setTimeout(() => {
      window.open(fallbackUrl, "_blank");
    }, 2000);
  } else {
    // 데스크톱에서는 티맵 웹으로 이동
    const webUrl = `https://tmap.life/route/search?name=${encodeURIComponent(
      placeName + " " + address
    )}`;
    window.open(webUrl, "_blank");
  }
}

// 카카오 SDK 초기화
function initKakao() {
  console.log("🔗 카카오 SDK 초기화 시도...");

  // SDK가 로드될 때까지 대기
  const checkKakaoSDK = () => {
    if (typeof Kakao !== "undefined") {
      try {
        Kakao.init("de64bfd6df931841a5c7c798d76c9515");
        console.log("✅ 카카오 SDK 초기화 성공:", Kakao.isInitialized());
      } catch (error) {
        console.error("❌ 카카오 SDK 초기화 실패:", error);
      }
    } else {
      // SDK가 아직 로드되지 않았으면 100ms 후 다시 시도
      setTimeout(checkKakaoSDK, 100);
    }
  };

  checkKakaoSDK();
}

// 카카오톡 공유
async function shareKakao() {
  console.log("📱 카카오톡 공유 시도...");

  const title = "백혁재 ♥ 최진주 결혼합니다";
  const desc = "1월 18일 오전 11시 30분\n문래역 JK아트컨벤션 4층 그랜드홀";
  const url = window.location.href;

  try {
    // 카카오 SDK가 초기화되었는지 확인
    if (typeof Kakao !== "undefined" && Kakao.isInitialized()) {
      console.log("✅ 카카오 SDK 사용하여 공유");
      await Kakao.Share.sendDefault({
        objectType: "feed",
        content: {
          title,
          description: desc,
          imageUrl:
            window.location.origin + "/assets/images/20250918_225238_2.png",
          link: { mobileWebUrl: url, webUrl: url },
        },
        buttons: [
          { title: "청첩장 열기", link: { mobileWebUrl: url, webUrl: url } },
        ],
      });
      console.log("✅ 카카오톡 공유 성공");
    } else {
      throw new Error("Kakao SDK not initialized");
    }
  } catch (e) {
    console.warn("❌ 카카오 공유 실패:", e);

    // 카카오 SDK 실패 시 fallback
    if (navigator.share) {
      try {
        console.log("📱 Web Share API 사용");
        await navigator.share({ title, text: desc, url });
        console.log("✅ Web Share API 공유 성공");
        return;
      } catch (shareError) {
        console.warn("❌ Web Share API 실패:", shareError);
      }
    }

    // 모든 방법 실패 시 링크 복사
    try {
      await navigator.clipboard?.writeText(url);
      alert("링크를 복사했습니다.");
      console.log("✅ 링크 복사 성공");
    } catch (clipboardError) {
      console.error("❌ 링크 복사 실패:", clipboardError);
      alert("공유 기능을 사용할 수 없습니다.");
    }
  }
}

// 링크 복사
function copyLink() {
  navigator.clipboard
    .writeText(window.location.href)
    .then(function () {
      alert("링크가 복사되었습니다.");
    })
    .catch(function (err) {
      console.error("복사 실패:", err);
      alert("복사에 실패했습니다.");
    });
}

// 지도 초기화 (네이버 지도 API)
function initMap() {
  if (typeof naver !== "undefined") {
    const mapOptions = {
      center: new naver.maps.LatLng(37.5748439, 126.9790021),
      zoom: 17,
    };

    const map = new naver.maps.Map("map", mapOptions);

    const marker = new naver.maps.Marker({
      position: new naver.maps.LatLng(37.5748439, 126.9790021),
      map: map,
    });
  }
}

// 확대 방지 초기화
function initZoomPrevention() {
  console.log("🔒 확대 방지 초기화...");

  // 더블탭 확대 방지 (지도 영역 제외)
  let lastTouchEnd = 0;
  document.addEventListener(
    "touchend",
    function (event) {
      // 지도 컨테이너 내부는 제외
      if (event.target.closest(".zoomable-map-container")) {
        return;
      }

      const now = new Date().getTime();
      if (now - lastTouchEnd <= 300) {
        event.preventDefault();
      }
      lastTouchEnd = now;
    },
    false
  );

  // 핀치 줌 방지 (지도 영역 제외)
  document.addEventListener(
    "touchstart",
    function (event) {
      // 지도 컨테이너 내부는 제외
      if (event.target.closest(".zoomable-map-container")) {
        return;
      }

      if (event.touches.length > 1) {
        event.preventDefault();
      }
    },
    { passive: false }
  );

  document.addEventListener(
    "touchmove",
    function (event) {
      // 지도 컨테이너 내부는 제외
      if (event.target.closest(".zoomable-map-container")) {
        return;
      }

      if (event.touches.length > 1) {
        event.preventDefault();
      }
    },
    { passive: false }
  );

  // 휠 줌 방지 (데스크톱, 지도 영역 제외)
  document.addEventListener(
    "wheel",
    function (event) {
      // 지도 컨테이너 내부는 제외
      if (event.target.closest(".zoomable-map-container")) {
        return;
      }

      if (event.ctrlKey) {
        event.preventDefault();
      }
    },
    { passive: false }
  );

  // 키보드 줌 방지 (Ctrl + +/-)
  document.addEventListener("keydown", function (event) {
    if (
      event.ctrlKey &&
      (event.key === "+" || event.key === "-" || event.key === "=")
    ) {
      event.preventDefault();
    }
  });

  console.log("🔒 확대 방지 설정 완료");
}

// 지도 확대/축소 기능 초기화
let mapZoomLevel = 1;

function initZoomableMap() {
  console.log("🗺️ 지도 확대/축소 초기화...");

  const mapContainer = document.getElementById("zoomable-map");
  if (!mapContainer) {
    console.log("지도 컨테이너를 찾을 수 없습니다.");
    return;
  }

  // 휠 줌 (지도 영역에서만)
  mapContainer.addEventListener(
    "wheel",
    function (event) {
      event.preventDefault();
      const delta = event.deltaY > 0 ? -0.1 : 0.1;
      setMapZoom(mapZoomLevel + delta);
    },
    { passive: false }
  );

  // 지도 영역에서 핀치 줌 완전 차단
  const mapContainerParent = mapContainer.closest(".zoomable-map-container");
  if (mapContainerParent) {
    mapContainerParent.addEventListener(
      "touchstart",
      function (event) {
        if (event.touches.length > 1) {
          event.preventDefault();
          event.stopPropagation();
        }
      },
      { passive: false }
    );

    mapContainerParent.addEventListener(
      "touchmove",
      function (event) {
        if (event.touches.length > 1) {
          event.preventDefault();
          event.stopPropagation();
        }
      },
      { passive: false }
    );

    mapContainerParent.addEventListener(
      "gesturestart",
      function (event) {
        event.preventDefault();
      },
      { passive: false }
    );

    mapContainerParent.addEventListener(
      "gesturechange",
      function (event) {
        event.preventDefault();
      },
      { passive: false }
    );

    mapContainerParent.addEventListener(
      "gestureend",
      function (event) {
        event.preventDefault();
      },
      { passive: false }
    );
  }

  console.log("🗺️ 지도 확대/축소 설정 완료");
}

// 지도 확대/축소 함수
function zoomMap(direction) {
  const step = 0.2;
  if (direction === "in") {
    setMapZoom(mapZoomLevel + step);
  } else if (direction === "out") {
    setMapZoom(mapZoomLevel - step);
  }
}

// 줌 레벨 설정
function setMapZoom(newZoom) {
  const minZoom = 1.0;
  const maxZoom = 3.0;

  mapZoomLevel = Math.max(minZoom, Math.min(maxZoom, newZoom));

  updateMapTransform();
  updateZoomButtons();
}

// 지도 변환 업데이트 (이미지에만 적용)
function updateMapTransform() {
  const mapContainer = document.getElementById("zoomable-map");
  if (!mapContainer) return;

  const mapImage = mapContainer.querySelector("img");
  if (!mapImage) return;

  const transform = `translate(-50%, -50%) scale(${mapZoomLevel})`;
  mapImage.style.transform = transform;
}

// 줌 버튼 상태 업데이트
function updateZoomButtons() {
  const zoomInBtn = document.querySelector(".zoom-in");
  const zoomOutBtn = document.querySelector(".zoom-out");

  if (zoomInBtn) {
    zoomInBtn.style.opacity = mapZoomLevel >= 3.0 ? "0.5" : "1";
    zoomInBtn.style.cursor = mapZoomLevel >= 3.0 ? "not-allowed" : "pointer";
  }

  if (zoomOutBtn) {
    zoomOutBtn.style.opacity = mapZoomLevel <= 1.0 ? "0.5" : "1";
    zoomOutBtn.style.cursor = mapZoomLevel <= 1.0 ? "not-allowed" : "pointer";
  }
}

// 외부 스크립트 로드 후 지도 초기화
window.addEventListener("load", function () {
  // 네이버 지도 API가 로드되면 지도 초기화
  if (typeof naver !== "undefined") {
    initMap();
  }
});
