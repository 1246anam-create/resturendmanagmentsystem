/* Banner Slider - Animation and auto-play logic */
(function () {
    "use strict";

    var bannerCurrent = 0;
    var bannerTimer = null;
    var bannerSlides = [];
    var bannerDots = [];

    function initBannerSlider() {
        var slider = document.getElementById("bannerSlider");
        if (!slider) return;
        bannerSlides = slider.querySelectorAll(".banner-slide");
        bannerDots = document.querySelectorAll(".banner-dot");
        if (bannerSlides.length <= 1) return;

        var first = bannerSlides[0];
        var dur = first.getAttribute("data-duration") || 800;
        first.style.setProperty("--banner-duration", dur + "ms");

        var autoPlay = slider.getAttribute("data-autoplay") === "1";
        var interval = parseInt(slider.getAttribute("data-interval") || "5000", 10);

        if (autoPlay) {
            bannerTimer = setInterval(bannerNext, interval);
        }
    }

    window.bannerNext = function () {
        if (bannerSlides.length <= 1) return;
        bannerGoTo((bannerCurrent + 1) % bannerSlides.length);
    };

    window.bannerPrev = function () {
        if (bannerSlides.length <= 1) return;
        bannerGoTo((bannerCurrent - 1 + bannerSlides.length) % bannerSlides.length);
    };

    window.bannerGoTo = function (index) {
        if (index < 0 || index >= bannerSlides.length) return;
        bannerSlides[bannerCurrent].style.display = "none";
        if (bannerDots[bannerCurrent]) bannerDots[bannerCurrent].classList.remove("active");

        bannerCurrent = index;
        var slide = bannerSlides[bannerCurrent];
        slide.style.display = "flex";
        slide.style.animation = "none";
        slide.offsetHeight;
        var anim = slide.getAttribute("data-animation") || "fade";
        var dur = slide.getAttribute("data-duration") || 800;
        slide.style.setProperty("--banner-duration", dur + "ms");
        slide.style.animation = "";
        slide.setAttribute("data-animation", anim);

        if (bannerDots[bannerCurrent]) bannerDots[bannerCurrent].classList.add("active");
    };

    document.addEventListener("DOMContentLoaded", function () {
        initBannerSlider();
    });
})();
