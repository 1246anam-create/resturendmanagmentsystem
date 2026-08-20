"""CMS blueprint: website content management (header, footer, banners, services,
about, theme, branding, restaurant settings). Admin controlled."""
from flask import (
    Blueprint, render_template, redirect, url_for, request, flash, jsonify, abort
)
from flask_login import login_required, current_user
from extensions import db
from models.settings import (
    HeaderSettings, FooterSettings, Banner, Service, AboutContent,
    RestaurantSettings, ThemeSettings,
)
from utils.helpers import save_uploaded_file, log_activity
from utils.validators import sanitize_int, sanitize_float
from datetime import datetime

bp = Blueprint("cms", __name__, url_prefix="/admin/cms")


@bp.before_request
def require_admin():
    if not current_user.is_authenticated or current_user.role.name != "ADMIN":
        abort(403)


# ---------------------------------------------------------------------------
# HEADER
# ---------------------------------------------------------------------------
@bp.route("/header", methods=["GET", "POST"])
def header():
    h = HeaderSettings.query.first()
    if not h:
        h = HeaderSettings()
        db.session.add(h)
        db.session.commit()
    if request.method == "POST":
        h.restaurant_name = request.form.get("restaurant_name", h.restaurant_name)
        h.cta_text = request.form.get("cta_text", h.cta_text)
        h.cta_link = request.form.get("cta_link", h.cta_link)
        h.contact_phone = request.form.get("contact_phone", h.contact_phone)
        h.contact_email = request.form.get("contact_email", h.contact_email)
        h.show_reservation_button = bool(request.form.get("show_reservation_button"))
        if request.files.get("logo"):
            path = save_uploaded_file(request.files["logo"], "logo")
            if path:
                h.logo = path
        db.session.commit()
        log_activity(current_user, "header_updated", "cms", request.remote_addr)
        flash("Header updated.", "success")
        return redirect(url_for("cms.header"))
    return render_template("admin/cms_header.html", header=h)


# ---------------------------------------------------------------------------
# FOOTER
# ---------------------------------------------------------------------------
@bp.route("/footer", methods=["GET", "POST"])
def footer():
    f = FooterSettings.query.first()
    if not f:
        f = FooterSettings()
        db.session.add(f)
        db.session.commit()
    if request.method == "POST":
        f.description = request.form.get("description", f.description)
        f.facebook = request.form.get("facebook", f.facebook)
        f.instagram = request.form.get("instagram", f.instagram)
        f.youtube = request.form.get("youtube", f.youtube)
        f.twitter = request.form.get("twitter", f.twitter)
        f.linkedin = request.form.get("linkedin", f.linkedin)
        f.opening_hours = request.form.get("opening_hours", f.opening_hours)
        f.copyright_text = request.form.get("copyright_text", f.copyright_text)
        f.privacy_policy_link = request.form.get("privacy_policy_link", f.privacy_policy_link)
        f.terms_link = request.form.get("terms_link", f.terms_link)
        db.session.commit()
        log_activity(current_user, "footer_updated", "cms", request.remote_addr)
        flash("Footer updated.", "success")
        return redirect(url_for("cms.footer"))
    return render_template("admin/cms_footer.html", footer=f)


# ---------------------------------------------------------------------------
# BANNERS
# ---------------------------------------------------------------------------
@bp.route("/banners")
def banners():
    banners = Banner.query.order_by(Banner.display_order).all()
    return render_template("admin/cms_banners.html", banners=banners)


@bp.route("/banners/add", methods=["GET", "POST"])
def banner_add():
    if request.method == "POST":
        image = None
        if request.files.get("image") and request.files["image"].filename:
            image = save_uploaded_file(request.files["image"], "banners")
            if image is None:
                flash("Invalid image file. Please upload a valid image (PNG, JPG, JPEG, GIF, WebP, SVG, ICO) under 16MB.", "danger")
                return render_template("admin/cms_banner_form.html", banner=None)
        if not image and request.form.get("image_url"):
            image = request.form.get("image_url").strip()
        b = Banner(
            title=request.form.get("title", "").strip(),
            description=request.form.get("description", ""),
            image=image or "uploads/banners/default.jpg",
            button_text=request.form.get("button_text", "Explore Menu"),
            button_link=request.form.get("button_link", "/menu"),
            secondary_button_text=request.form.get("secondary_button_text", ""),
            secondary_button_link=request.form.get("secondary_button_link", ""),
            display_order=sanitize_int(request.form.get("display_order", 0)),
            status=request.form.get("status", "active"),
            animation_type=request.form.get("animation_type", "fade"),
            animation_duration=sanitize_int(request.form.get("animation_duration", 800)),
            auto_play=bool(request.form.get("auto_play")),
            auto_play_interval=sanitize_int(request.form.get("auto_play_interval", 5000)),
        )
        db.session.add(b)
        db.session.commit()
        log_activity(current_user, "banner_added", "cms", request.remote_addr)
        flash("Banner added.", "success")
        return redirect(url_for("cms.banners"))
    return render_template("admin/cms_banner_form.html", banner=None)


@bp.route("/banners/<int:bid>/edit", methods=["GET", "POST"])
def banner_edit(bid):
    b = Banner.query.get_or_404(bid)
    if request.method == "POST":
        b.title = request.form.get("title", "").strip()
        b.description = request.form.get("description", "")
        b.button_text = request.form.get("button_text", "Explore Menu")
        b.button_link = request.form.get("button_link", "/menu")
        b.secondary_button_text = request.form.get("secondary_button_text", "")
        b.secondary_button_link = request.form.get("secondary_button_link", "")
        b.display_order = sanitize_int(request.form.get("display_order", 0))
        b.status = request.form.get("status", "active")
        b.animation_type = request.form.get("animation_type", "fade")
        b.animation_duration = sanitize_int(request.form.get("animation_duration", 800))
        b.auto_play = bool(request.form.get("auto_play"))
        b.auto_play_interval = sanitize_int(request.form.get("auto_play_interval", 5000))
        if request.files.get("image") and request.files["image"].filename:
            path = save_uploaded_file(request.files["image"], "banners")
            if path is None:
                flash("Invalid image file. Please upload a valid image (PNG, JPG, JPEG, GIF, WebP, SVG, ICO) under 16MB.", "danger")
                return render_template("admin/cms_banner_form.html", banner=b)
            b.image = path
        elif request.form.get("image_url"):
            b.image = request.form.get("image_url").strip()
        db.session.commit()
        log_activity(current_user, "banner_updated", "cms", request.remote_addr)
        flash("Banner updated.", "success")
        return redirect(url_for("cms.banners"))
    return render_template("admin/cms_banner_form.html", banner=b)


@bp.route("/banners/<int:bid>/delete", methods=["POST"])
def banner_delete(bid):
    b = Banner.query.get_or_404(bid)
    db.session.delete(b)
    db.session.commit()
    return jsonify({"ok": True})


# ---------------------------------------------------------------------------
# SERVICES
# ---------------------------------------------------------------------------
@bp.route("/services")
def services():
    services = Service.query.order_by(Service.display_order).all()
    return render_template("admin/cms_services.html", services=services)


@bp.route("/services/add", methods=["GET", "POST"])
def service_add():
    if request.method == "POST":
        image = None
        if request.files.get("image"):
            image = save_uploaded_file(request.files["image"], "services")
        s = Service(
            title=request.form.get("title", "").strip(),
            description=request.form.get("description", ""),
            icon=request.form.get("icon", "utensils"),
            image=image, button_text=request.form.get("button_text", "Learn More"),
            button_link=request.form.get("button_link", "#"),
            display_order=sanitize_int(request.form.get("display_order", 0)),
            status=request.form.get("status", "active"),
        )
        db.session.add(s)
        db.session.commit()
        log_activity(current_user, "service_added", "cms", request.remote_addr)
        flash("Service added.", "success")
        return redirect(url_for("cms.services"))
    return render_template("admin/cms_service_form.html", service=None)


@bp.route("/services/<int:sid>/edit", methods=["GET", "POST"])
def service_edit(sid):
    s = Service.query.get_or_404(sid)
    if request.method == "POST":
        s.title = request.form.get("title", "").strip()
        s.description = request.form.get("description", "")
        s.icon = request.form.get("icon", "utensils")
        s.button_text = request.form.get("button_text", "Learn More")
        s.button_link = request.form.get("button_link", "#")
        s.display_order = sanitize_int(request.form.get("display_order", 0))
        s.status = request.form.get("status", "active")
        if request.files.get("image"):
            path = save_uploaded_file(request.files["image"], "services")
            if path:
                s.image = path
        db.session.commit()
        log_activity(current_user, "service_updated", "cms", request.remote_addr)
        flash("Service updated.", "success")
        return redirect(url_for("cms.services"))
    return render_template("admin/cms_service_form.html", service=s)


@bp.route("/services/<int:sid>/delete", methods=["POST"])
def service_delete(sid):
    s = Service.query.get_or_404(sid)
    db.session.delete(s)
    db.session.commit()
    return jsonify({"ok": True})


# ---------------------------------------------------------------------------
# ABOUT US
# ---------------------------------------------------------------------------
@bp.route("/about", methods=["GET", "POST"])
def about():
    a = AboutContent.query.first()
    if not a:
        a = AboutContent()
        db.session.add(a)
        db.session.commit()
    if request.method == "POST":
        a.story_title = request.form.get("story_title", a.story_title)
        a.story = request.form.get("story", a.story)
        a.mission_title = request.form.get("mission_title", a.mission_title)
        a.mission = request.form.get("mission", a.mission)
        a.vision_title = request.form.get("vision_title", a.vision_title)
        a.vision = request.form.get("vision", a.vision)
        a.history = request.form.get("history", a.history)
        a.chef_name = request.form.get("chef_name", a.chef_name)
        a.chef_title = request.form.get("chef_title", a.chef_title)
        a.chef_bio = request.form.get("chef_bio", a.chef_bio)
        a.stat1_label = request.form.get("stat1_label", a.stat1_label)
        a.stat1_value = request.form.get("stat1_value", a.stat1_value)
        a.stat2_label = request.form.get("stat2_label", a.stat2_label)
        a.stat2_value = request.form.get("stat2_value", a.stat2_value)
        a.stat3_label = request.form.get("stat3_label", a.stat3_label)
        a.stat3_value = request.form.get("stat3_value", a.stat3_value)
        a.stat4_label = request.form.get("stat4_label", a.stat4_label)
        a.stat4_value = request.form.get("stat4_value", a.stat4_value)
        for field, folder in [("chef_image", "restaurant"), ("image_1", "restaurant"),
                              ("image_2", "restaurant"), ("image_3", "restaurant")]:
            if request.files.get(field):
                path = save_uploaded_file(request.files[field], folder)
                if path:
                    setattr(a, field, path)
        db.session.commit()
        log_activity(current_user, "about_updated", "cms", request.remote_addr)
        flash("About content updated.", "success")
        return redirect(url_for("cms.about"))
    return render_template("admin/cms_about.html", about=a)


# ---------------------------------------------------------------------------
# RESTAURANT SETTINGS
# ---------------------------------------------------------------------------
@bp.route("/settings", methods=["GET", "POST"])
def settings():
    r = RestaurantSettings.query.first()
    if not r:
        r = RestaurantSettings()
        db.session.add(r)
        db.session.commit()
    if request.method == "POST":
        r.name = request.form.get("name", r.name)
        r.phone = request.form.get("phone", r.phone)
        r.email = request.form.get("email", r.email)
        r.address = request.form.get("address", r.address)
        r.currency = request.form.get("currency", r.currency)
        r.currency_symbol = request.form.get("currency_symbol", r.currency_symbol)
        r.tax_rate = sanitize_float(request.form.get("tax_rate", r.tax_rate))
        r.delivery_charges = sanitize_float(request.form.get("delivery_charges", r.delivery_charges))
        r.opening_hours = request.form.get("opening_hours", r.opening_hours)
        r.status = request.form.get("status", r.status)
        if request.files.get("favicon"):
            path = save_uploaded_file(request.files["favicon"], "favicon")
            if path:
                r.favicon = path
        db.session.commit()
        log_activity(current_user, "settings_updated", "settings", request.remote_addr)
        flash("Restaurant settings updated.", "success")
        return redirect(url_for("cms.settings"))
    return render_template("admin/cms_settings.html", settings=r)


# ---------------------------------------------------------------------------
# THEME & BRANDING
# ---------------------------------------------------------------------------
@bp.route("/theme", methods=["GET", "POST"])
def theme():
    t = ThemeSettings.query.first()
    if not t:
        t = ThemeSettings()
        db.session.add(t)
        db.session.commit()
    if request.method == "POST":
        t.primary_color = request.form.get("primary_color", t.primary_color)
        t.secondary_color = request.form.get("secondary_color", t.secondary_color)
        t.accent_color = request.form.get("accent_color", t.accent_color)
        t.background_color = request.form.get("background_color", t.background_color)
        t.surface_color = request.form.get("surface_color", t.surface_color)
        t.text_color = request.form.get("text_color", t.text_color)
        t.muted_text_color = request.form.get("muted_text_color", t.muted_text_color)
        t.button_color = request.form.get("button_color", t.button_color)
        t.font_family = request.form.get("font_family", t.font_family)
        t.border_radius = request.form.get("border_radius", t.border_radius)
        t.mode = request.form.get("mode", t.mode)
        db.session.commit()
        log_activity(current_user, "theme_updated", "theme", request.remote_addr)
        flash("Theme updated.", "success")
        return redirect(url_for("cms.theme"))
    return render_template("admin/cms_theme.html", theme=t)


@bp.route("/branding", methods=["GET", "POST"])
def branding():
    h = HeaderSettings.query.first()
    r = RestaurantSettings.query.first()
    if request.method == "POST":
        if request.files.get("logo"):
            path = save_uploaded_file(request.files["logo"], "logo")
            if path and h:
                h.logo = path
        if request.files.get("favicon"):
            path = save_uploaded_file(request.files["favicon"], "favicon")
            if path and r:
                r.favicon = path
        db.session.commit()
        log_activity(current_user, "branding_updated", "branding", request.remote_addr)
        flash("Branding updated.", "success")
        return redirect(url_for("cms.branding"))
    return render_template("admin/cms_branding.html", header=h, settings=r)
