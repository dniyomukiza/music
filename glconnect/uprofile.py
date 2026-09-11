
import os
from glconnect.models import*
from werkzeug.utils import secure_filename
from flask_login import login_required, current_user
from flask import current_app,render_template, request, redirect, url_for,Blueprint, flash


prof = Blueprint('prof', __name__)

@prof.route("/uprofile")
@login_required
def profile():
    return render_template("uprofile.html", user=current_user)

@prof.route("/edit", methods=["GET", "POST"])
@login_required
def edit_profile():
    if request.method == "POST":
        requested_email = (request.form.get("email") or "").strip().lower()
        current_email = (current_user.email or "").strip().lower()
        if requested_email != current_email:
            # Email is an account-recovery and transaction-identity field.
            # Require recent knowledge of the password before changing it.
            if not current_user.check_password(request.form.get("current_password") or ""):
                flash("Changing your email requires your current password.", "error")
                return render_template("edit_profile.html", user=current_user)
            if User.query.filter(
                db.and_(
                    db.func.lower(User.email) == requested_email,
                    User.user_id != current_user.user_id,
                )
            ).first():
                flash("That email address is already in use.", "error")
                return render_template("edit_profile.html", user=current_user)

        current_user.first_name = request.form["first_name"]
        current_user.last_name = request.form["last_name"]
        current_user.email = requested_email
        
        if "profile_picture" in request.files:
            file = request.files["profile_picture"]
            if file.filename:
                filename = secure_filename(file.filename)
                file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
                file.save(file_path)
                current_user.profile_picture = filename
        
        db.session.commit()
        return redirect(url_for("prof.profile"))
    return render_template("edit_profile.html", user=current_user)
