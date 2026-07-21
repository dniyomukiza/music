"""Remove retired podcaster/freelancer role data for the testing environment.

This is intentionally destructive and refuses to run in live data mode.
Existing blog posts are retained; only role labels and podcast submissions
belong to the retired features.
"""

import os
from pathlib import Path

from glconnect import create_app, db
from glconnect.data_lifecycle import is_live_data_mode
from glconnect.models import User, PodcastSubmission


def main() -> None:
    if is_live_data_mode():
        raise SystemExit("Refusing destructive retired-role cleanup in live data mode.")

    app, _socketio = create_app()
    with app.app_context():
        converted = User.query.filter_by(role="freelancer").update(
            {User.role: "blogger"}, synchronize_session=False
        )
        submissions = PodcastSubmission.query.all()
        removed_files = 0
        roots = [
            Path(app.root_path) / "static" / "podcasts",
            Path(app.root_path) / "static" / "temp_podcasts",
        ]
        for submission in submissions:
            if submission.file_path:
                candidate = Path(app.root_path) / submission.file_path
                if candidate.is_file():
                    candidate.unlink()
                    removed_files += 1
            db.session.delete(submission)
        db.session.commit()
        print(f"Converted freelancer accounts to blogger: {converted}")
        print(f"Removed podcast submissions: {len(submissions)}")
        print(f"Removed podcast files referenced by submissions: {removed_files}")


if __name__ == "__main__":
    main()
