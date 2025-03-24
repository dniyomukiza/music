
import os
from glconnect.models import*
from werkzeug.utils import secure_filename
from flask_login import login_required, current_user
from flask import current_app,render_template, request, redirect, url_for,Blueprint


prof = Blueprint('prof', __name__)

@prof.route("/uprofile")
@login_required
def profile():
    return render_template("uprofile.html", user=current_user)

@prof.route("/edit", methods=["GET", "POST"])
@login_required
def edit_profile():
    if request.method == "POST":
        current_user.first_name = request.form["first_name"]
        current_user.last_name = request.form["last_name"]
        current_user.email = request.form["email"]
        
        if "profile_picture" in request.files:
            file = request.files["profile_picture"]
            if file.filename:
                filename = secure_filename(file.filename)
                file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
                file.save(file_path)
                current_user.profile_picture = filename
        
        db.session.commit()
        return redirect(url_for("profile"))
    return render_template("edit_profile.html", user=current_user)