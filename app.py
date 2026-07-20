import sqlite3
import uuid
from functools import wraps
from pathlib import Path

from flask import (
    Flask,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from werkzeug.utils import secure_filename


# =========================================================
# 기본 경로
# =========================================================

BASE_DIR = Path(__file__).resolve().parent

DATABASE_DIR = BASE_DIR / "database"
DATABASE_PATH = DATABASE_DIR / "cores.db"

UPLOAD_FOLDER = BASE_DIR / "static" / "uploads"

ALLOWED_IMAGE_EXTENSIONS = {
    "png",
    "jpg",
    "jpeg",
    "webp",
    "gif",
}


# =========================================================
# Flask 설정
# =========================================================

app = Flask(__name__)

app.config["SECRET_KEY"] = "change-this-secret-key"
app.config["UPLOAD_FOLDER"] = str(UPLOAD_FOLDER)
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024


# 관리자 로그인 정보
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "1234"


# =========================================================
# 폴더 및 데이터베이스
# =========================================================

def create_required_folders():
    DATABASE_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    UPLOAD_FOLDER.mkdir(
        parents=True,
        exist_ok=True,
    )


def get_db_connection():
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row

    return connection


def initialize_database():
    create_required_folders()

    connection = get_db_connection()

    # 코어 테이블
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS cores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            grade TEXT NOT NULL,
            required_level INTEGER NOT NULL DEFAULT 0,
            effect TEXT NOT NULL,
            quantity INTEGER NOT NULL DEFAULT 0,
            obtain_location TEXT,
            description TEXT,
            image_filename TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    # 기존 코어 DB에 quantity가 없을 경우 자동 추가
    core_columns = connection.execute(
        """
        PRAGMA table_info(cores)
        """
    ).fetchall()

    core_column_names = {
        column["name"]
        for column in core_columns
    }

    if "quantity" not in core_column_names:
        connection.execute(
            """
            ALTER TABLE cores
            ADD COLUMN quantity INTEGER NOT NULL DEFAULT 0
            """
        )

    # 히든 직업 테이블
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS hidden_jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            category TEXT,
            conditions TEXT NOT NULL,
            prerequisite_quest TEXT,
            npc_name TEXT,
            npc_coordinates TEXT,
            description TEXT,
            image_filename TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    connection.commit()
    connection.close()


# =========================================================
# 로그인 확인
# =========================================================

def login_required(view_function):
    @wraps(view_function)
    def wrapped_view(*args, **kwargs):
        if not session.get("logged_in"):
            flash(
                "관리자 로그인이 필요합니다.",
                "error",
            )

            return redirect(
                url_for("login")
            )

        return view_function(
            *args,
            **kwargs,
        )

    return wrapped_view


# =========================================================
# 이미지 처리
# =========================================================

def allowed_image(filename):
    if "." not in filename:
        return False

    extension = filename.rsplit(
        ".",
        1,
    )[1].lower()

    return extension in ALLOWED_IMAGE_EXTENSIONS


def save_uploaded_image(image_file):
    if not image_file:
        return None

    if not image_file.filename:
        return None

    if not allowed_image(image_file.filename):
        raise ValueError(
            "이미지는 PNG, JPG, JPEG, WEBP, GIF 파일만 등록할 수 있습니다."
        )

    UPLOAD_FOLDER.mkdir(
        parents=True,
        exist_ok=True,
    )

    original_filename = secure_filename(
        image_file.filename
    )

    if not original_filename:
        original_filename = "image.png"

    extension = original_filename.rsplit(
        ".",
        1,
    )[1].lower()

    new_filename = (
        f"{uuid.uuid4().hex}.{extension}"
    )

    save_path = UPLOAD_FOLDER / new_filename

    image_file.save(
        str(save_path)
    )

    return new_filename


def delete_image_file(filename):
    if not filename:
        return

    image_path = UPLOAD_FOLDER / filename

    if image_path.exists() and image_path.is_file():
        image_path.unlink()


# =========================================================
# 기본 페이지
# =========================================================

@app.route("/")
def index():
    if session.get("logged_in"):
        return redirect(
            url_for("core_list")
        )

    return redirect(
        url_for("login")
    )


# =========================================================
# 로그인
# =========================================================

@app.route(
    "/login",
    methods=["GET", "POST"],
)
def login():
    if session.get("logged_in"):
        return redirect(
            url_for("core_list")
        )

    if request.method == "POST":
        username = request.form.get(
            "username",
            "",
        ).strip()

        password = request.form.get(
            "password",
            "",
        )

        if (
            username == ADMIN_USERNAME
            and password == ADMIN_PASSWORD
        ):
            session["logged_in"] = True
            session["username"] = username

            flash(
                "관리자 로그인이 완료되었습니다.",
                "success",
            )

            return redirect(
                url_for("core_list")
            )

        flash(
            "아이디 또는 비밀번호가 올바르지 않습니다.",
            "error",
        )

    return render_template(
        "login.html"
    )


@app.route("/logout")
def logout():
    session.clear()

    flash(
        "로그아웃되었습니다.",
        "success",
    )

    return redirect(
        url_for("login")
    )


# =========================================================
# 코어 목록
# =========================================================

@app.route("/cores")
@login_required
def core_list():
    search = request.args.get(
        "search",
        "",
    ).strip()

    connection = get_db_connection()

    if search:
        cores = connection.execute(
            """
            SELECT *
            FROM cores
            WHERE name LIKE ?
               OR grade LIKE ?
               OR effect LIKE ?
               OR obtain_location LIKE ?
            ORDER BY id DESC
            """,
            (
                f"%{search}%",
                f"%{search}%",
                f"%{search}%",
                f"%{search}%",
            ),
        ).fetchall()

    else:
        cores = connection.execute(
            """
            SELECT *
            FROM cores
            ORDER BY id DESC
            """
        ).fetchall()

    total_quantity_row = connection.execute(
        """
        SELECT COALESCE(SUM(quantity), 0) AS total_quantity
        FROM cores
        """
    ).fetchone()

    total_quantity = total_quantity_row["total_quantity"]

    connection.close()

    return render_template(
        "cores.html",
        cores=cores,
        search=search,
        total_quantity=total_quantity,
    )


# =========================================================
# 코어 등록
# =========================================================

@app.route(
    "/cores/new",
    methods=["GET", "POST"],
)
@login_required
def create_core():
    if request.method == "POST":
        name = request.form.get(
            "name",
            "",
        ).strip()

        grade = request.form.get(
            "grade",
            "",
        ).strip()

        required_level_text = request.form.get(
            "required_level",
            "0",
        ).strip()

        quantity_text = request.form.get(
            "quantity",
            "0",
        ).strip()

        effect = request.form.get(
            "effect",
            "",
        ).strip()

        obtain_location = request.form.get(
            "obtain_location",
            "",
        ).strip()

        description = request.form.get(
            "description",
            "",
        ).strip()

        image_file = request.files.get(
            "image"
        )

        if not name:
            flash(
                "코어 이름을 입력해주세요.",
                "error",
            )

            return render_template(
                "core_form.html",
                page_title="코어 등록",
                core=None,
            )

        if not grade:
            flash(
                "코어 등급을 선택해주세요.",
                "error",
            )

            return render_template(
                "core_form.html",
                page_title="코어 등록",
                core=None,
            )

        if not effect:
            flash(
                "부여 효과를 입력해주세요.",
                "error",
            )

            return render_template(
                "core_form.html",
                page_title="코어 등록",
                core=None,
            )

        try:
            required_level = int(
                required_level_text
            )

            quantity = int(
                quantity_text
            )

        except ValueError:
            flash(
                "레벨과 보유 수량은 숫자로 입력해주세요.",
                "error",
            )

            return render_template(
                "core_form.html",
                page_title="코어 등록",
                core=None,
            )

        if required_level < 0 or quantity < 0:
            flash(
                "레벨과 보유 수량은 0 이상이어야 합니다.",
                "error",
            )

            return render_template(
                "core_form.html",
                page_title="코어 등록",
                core=None,
            )

        try:
            image_filename = save_uploaded_image(
                image_file
            )

        except ValueError as error:
            flash(
                str(error),
                "error",
            )

            return render_template(
                "core_form.html",
                page_title="코어 등록",
                core=None,
            )

        connection = get_db_connection()

        connection.execute(
            """
            INSERT INTO cores (
                name,
                grade,
                required_level,
                effect,
                quantity,
                obtain_location,
                description,
                image_filename
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                name,
                grade,
                required_level,
                effect,
                quantity,
                obtain_location,
                description,
                image_filename,
            ),
        )

        connection.commit()
        connection.close()

        flash(
            f"'{name}' 코어가 등록되었습니다.",
            "success",
        )

        return redirect(
            url_for("core_list")
        )

    return render_template(
        "core_form.html",
        page_title="코어 등록",
        core=None,
    )


# =========================================================
# 코어 수정
# =========================================================

@app.route(
    "/cores/<int:core_id>/edit",
    methods=["GET", "POST"],
)
@login_required
def edit_core(core_id):
    connection = get_db_connection()

    core = connection.execute(
        """
        SELECT *
        FROM cores
        WHERE id = ?
        """,
        (core_id,),
    ).fetchone()

    connection.close()

    if core is None:
        flash(
            "해당 코어를 찾을 수 없습니다.",
            "error",
        )

        return redirect(
            url_for("core_list")
        )

    if request.method == "POST":
        name = request.form.get(
            "name",
            "",
        ).strip()

        grade = request.form.get(
            "grade",
            "",
        ).strip()

        required_level_text = request.form.get(
            "required_level",
            "0",
        ).strip()

        quantity_text = request.form.get(
            "quantity",
            "0",
        ).strip()

        effect = request.form.get(
            "effect",
            "",
        ).strip()

        obtain_location = request.form.get(
            "obtain_location",
            "",
        ).strip()

        description = request.form.get(
            "description",
            "",
        ).strip()

        image_file = request.files.get(
            "image"
        )

        delete_current_image = (
            request.form.get(
                "delete_current_image"
            )
            == "yes"
        )

        if not name or not grade or not effect:
            flash(
                "필수 항목을 모두 입력해주세요.",
                "error",
            )

            return redirect(
                url_for(
                    "edit_core",
                    core_id=core_id,
                )
            )

        try:
            required_level = int(
                required_level_text
            )

            quantity = int(
                quantity_text
            )

        except ValueError:
            flash(
                "레벨과 보유 수량은 숫자로 입력해주세요.",
                "error",
            )

            return redirect(
                url_for(
                    "edit_core",
                    core_id=core_id,
                )
            )

        if required_level < 0 or quantity < 0:
            flash(
                "레벨과 보유 수량은 0 이상이어야 합니다.",
                "error",
            )

            return redirect(
                url_for(
                    "edit_core",
                    core_id=core_id,
                )
            )

        image_filename = core["image_filename"]

        if delete_current_image and image_filename:
            delete_image_file(
                image_filename
            )

            image_filename = None

        if image_file and image_file.filename:
            try:
                new_image_filename = save_uploaded_image(
                    image_file
                )

            except ValueError as error:
                flash(
                    str(error),
                    "error",
                )

                return redirect(
                    url_for(
                        "edit_core",
                        core_id=core_id,
                    )
                )

            if image_filename:
                delete_image_file(
                    image_filename
                )

            image_filename = new_image_filename

        connection = get_db_connection()

        connection.execute(
            """
            UPDATE cores
            SET name = ?,
                grade = ?,
                required_level = ?,
                effect = ?,
                quantity = ?,
                obtain_location = ?,
                description = ?,
                image_filename = ?
            WHERE id = ?
            """,
            (
                name,
                grade,
                required_level,
                effect,
                quantity,
                obtain_location,
                description,
                image_filename,
                core_id,
            ),
        )

        connection.commit()
        connection.close()

        flash(
            f"'{name}' 코어 정보가 수정되었습니다.",
            "success",
        )

        return redirect(
            url_for("core_list")
        )

    return render_template(
        "core_form.html",
        page_title="코어 수정",
        core=core,
    )


# =========================================================
# 코어 수량 변경
# =========================================================

@app.route(
    "/cores/<int:core_id>/quantity",
    methods=["POST"],
)
@login_required
def adjust_core_quantity(core_id):
    try:
        amount = int(
            request.form.get(
                "amount",
                "0",
            )
        )

    except ValueError:
        flash(
            "올바르지 않은 수량입니다.",
            "error",
        )

        return redirect(
            url_for("core_list")
        )

    if amount not in {
        -10,
        -1,
        1,
        10,
    }:
        flash(
            "허용되지 않은 수량 변경입니다.",
            "error",
        )

        return redirect(
            url_for("core_list")
        )

    connection = get_db_connection()

    core = connection.execute(
        """
        SELECT *
        FROM cores
        WHERE id = ?
        """,
        (core_id,),
    ).fetchone()

    if core is None:
        connection.close()

        flash(
            "해당 코어를 찾을 수 없습니다.",
            "error",
        )

        return redirect(
            url_for("core_list")
        )

    new_quantity = max(
        0,
        core["quantity"] + amount,
    )

    connection.execute(
        """
        UPDATE cores
        SET quantity = ?
        WHERE id = ?
        """,
        (
            new_quantity,
            core_id,
        ),
    )

    connection.commit()
    connection.close()

    return redirect(
        url_for("core_list")
    )


# =========================================================
# 코어 삭제
# =========================================================

@app.route(
    "/cores/<int:core_id>/delete",
    methods=["POST"],
)
@login_required
def delete_core(core_id):
    connection = get_db_connection()

    core = connection.execute(
        """
        SELECT *
        FROM cores
        WHERE id = ?
        """,
        (core_id,),
    ).fetchone()

    if core is None:
        connection.close()

        flash(
            "해당 코어를 찾을 수 없습니다.",
            "error",
        )

        return redirect(
            url_for("core_list")
        )

    connection.execute(
        """
        DELETE FROM cores
        WHERE id = ?
        """,
        (core_id,),
    )

    connection.commit()
    connection.close()

    delete_image_file(
        core["image_filename"]
    )

    flash(
        f"'{core['name']}' 코어가 삭제되었습니다.",
        "success",
    )

    return redirect(
        url_for("core_list")
    )


# =========================================================
# 히든 직업 목록
# =========================================================

@app.route("/hidden-jobs")
@login_required
def hidden_job_list():
    search = request.args.get(
        "search",
        "",
    ).strip()

    connection = get_db_connection()

    if search:
        hidden_jobs = connection.execute(
            """
            SELECT *
            FROM hidden_jobs
            WHERE name LIKE ?
               OR category LIKE ?
               OR conditions LIKE ?
               OR prerequisite_quest LIKE ?
               OR npc_name LIKE ?
               OR npc_coordinates LIKE ?
            ORDER BY id DESC
            """,
            (
                f"%{search}%",
                f"%{search}%",
                f"%{search}%",
                f"%{search}%",
                f"%{search}%",
                f"%{search}%",
            ),
        ).fetchall()

    else:
        hidden_jobs = connection.execute(
            """
            SELECT *
            FROM hidden_jobs
            ORDER BY id DESC
            """
        ).fetchall()

    connection.close()

    return render_template(
        "hidden_jobs.html",
        hidden_jobs=hidden_jobs,
        search=search,
    )


# =========================================================
# 히든 직업 상세보기
# =========================================================

@app.route("/hidden-jobs/<int:job_id>")
@login_required
def hidden_job_detail(job_id):
    connection = get_db_connection()

    hidden_job = connection.execute(
        """
        SELECT *
        FROM hidden_jobs
        WHERE id = ?
        """,
        (job_id,),
    ).fetchone()

    connection.close()

    if hidden_job is None:
        flash(
            "해당 히든 직업을 찾을 수 없습니다.",
            "error",
        )

        return redirect(
            url_for("hidden_job_list")
        )

    return render_template(
        "hidden_job_detail.html",
        hidden_job=hidden_job,
    )


# =========================================================
# 히든 직업 등록
# =========================================================

@app.route(
    "/hidden-jobs/new",
    methods=["GET", "POST"],
)
@login_required
def create_hidden_job():
    if request.method == "POST":
        name = request.form.get(
            "name",
            "",
        ).strip()

        category = request.form.get(
            "category",
            "",
        ).strip()

        conditions = request.form.get(
            "conditions",
            "",
        ).strip()

        prerequisite_quest = request.form.get(
            "prerequisite_quest",
            "",
        ).strip()

        npc_name = request.form.get(
            "npc_name",
            "",
        ).strip()

        npc_coordinates = request.form.get(
            "npc_coordinates",
            "",
        ).strip()

        description = request.form.get(
            "description",
            "",
        ).strip()

        image_file = request.files.get(
            "image"
        )

        if not name:
            flash(
                "히든 직업명을 입력해주세요.",
                "error",
            )

            return render_template(
                "hidden_job_form.html",
                page_title="히든 직업 등록",
                hidden_job=None,
            )

        if not conditions:
            flash(
                "획득 조건을 입력해주세요.",
                "error",
            )

            return render_template(
                "hidden_job_form.html",
                page_title="히든 직업 등록",
                hidden_job=None,
            )

        try:
            image_filename = save_uploaded_image(
                image_file
            )

        except ValueError as error:
            flash(
                str(error),
                "error",
            )

            return render_template(
                "hidden_job_form.html",
                page_title="히든 직업 등록",
                hidden_job=None,
            )

        connection = get_db_connection()

        connection.execute(
            """
            INSERT INTO hidden_jobs (
                name,
                category,
                conditions,
                prerequisite_quest,
                npc_name,
                npc_coordinates,
                description,
                image_filename
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                name,
                category,
                conditions,
                prerequisite_quest,
                npc_name,
                npc_coordinates,
                description,
                image_filename,
            ),
        )

        connection.commit()
        connection.close()

        flash(
            f"히든 직업 '{name}'이 등록되었습니다.",
            "success",
        )

        return redirect(
            url_for("hidden_job_list")
        )

    return render_template(
        "hidden_job_form.html",
        page_title="히든 직업 등록",
        hidden_job=None,
    )


# =========================================================
# 히든 직업 수정
# =========================================================

@app.route(
    "/hidden-jobs/<int:job_id>/edit",
    methods=["GET", "POST"],
)
@login_required
def edit_hidden_job(job_id):
    connection = get_db_connection()

    hidden_job = connection.execute(
        """
        SELECT *
        FROM hidden_jobs
        WHERE id = ?
        """,
        (job_id,),
    ).fetchone()

    connection.close()

    if hidden_job is None:
        flash(
            "해당 히든 직업을 찾을 수 없습니다.",
            "error",
        )

        return redirect(
            url_for("hidden_job_list")
        )

    if request.method == "POST":
        name = request.form.get(
            "name",
            "",
        ).strip()

        category = request.form.get(
            "category",
            "",
        ).strip()

        conditions = request.form.get(
            "conditions",
            "",
        ).strip()

        prerequisite_quest = request.form.get(
            "prerequisite_quest",
            "",
        ).strip()

        npc_name = request.form.get(
            "npc_name",
            "",
        ).strip()

        npc_coordinates = request.form.get(
            "npc_coordinates",
            "",
        ).strip()

        description = request.form.get(
            "description",
            "",
        ).strip()

        image_file = request.files.get(
            "image"
        )

        delete_current_image = (
            request.form.get(
                "delete_current_image"
            )
            == "yes"
        )

        if not name:
            flash(
                "히든 직업명을 입력해주세요.",
                "error",
            )

            return redirect(
                url_for(
                    "edit_hidden_job",
                    job_id=job_id,
                )
            )

        if not conditions:
            flash(
                "획득 조건을 입력해주세요.",
                "error",
            )

            return redirect(
                url_for(
                    "edit_hidden_job",
                    job_id=job_id,
                )
            )

        image_filename = hidden_job["image_filename"]

        if delete_current_image and image_filename:
            delete_image_file(
                image_filename
            )

            image_filename = None

        if image_file and image_file.filename:
            try:
                new_image_filename = save_uploaded_image(
                    image_file
                )

            except ValueError as error:
                flash(
                    str(error),
                    "error",
                )

                return redirect(
                    url_for(
                        "edit_hidden_job",
                        job_id=job_id,
                    )
                )

            if image_filename:
                delete_image_file(
                    image_filename
                )

            image_filename = new_image_filename

        connection = get_db_connection()

        connection.execute(
            """
            UPDATE hidden_jobs
            SET name = ?,
                category = ?,
                conditions = ?,
                prerequisite_quest = ?,
                npc_name = ?,
                npc_coordinates = ?,
                description = ?,
                image_filename = ?
            WHERE id = ?
            """,
            (
                name,
                category,
                conditions,
                prerequisite_quest,
                npc_name,
                npc_coordinates,
                description,
                image_filename,
                job_id,
            ),
        )

        connection.commit()
        connection.close()

        flash(
            f"히든 직업 '{name}'이 수정되었습니다.",
            "success",
        )

        return redirect(
            url_for(
                "hidden_job_detail",
                job_id=job_id,
            )
        )

    return render_template(
        "hidden_job_form.html",
        page_title="히든 직업 수정",
        hidden_job=hidden_job,
    )


# =========================================================
# 히든 직업 삭제
# =========================================================

@app.route(
    "/hidden-jobs/<int:job_id>/delete",
    methods=["POST"],
)
@login_required
def delete_hidden_job(job_id):
    connection = get_db_connection()

    hidden_job = connection.execute(
        """
        SELECT *
        FROM hidden_jobs
        WHERE id = ?
        """,
        (job_id,),
    ).fetchone()

    if hidden_job is None:
        connection.close()

        flash(
            "해당 히든 직업을 찾을 수 없습니다.",
            "error",
        )

        return redirect(
            url_for("hidden_job_list")
        )

    connection.execute(
        """
        DELETE FROM hidden_jobs
        WHERE id = ?
        """,
        (job_id,),
    )

    connection.commit()
    connection.close()

    delete_image_file(
        hidden_job["image_filename"]
    )

    flash(
        f"히든 직업 '{hidden_job['name']}'이 삭제되었습니다.",
        "success",
    )

    return redirect(
        url_for("hidden_job_list")
    )



# =========================================================
# 길드원 공개 지원 페이지
# =========================================================

@app.route("/support")
def support_page():
    search = request.args.get(
        "search",
        "",
    ).strip()

    connection = get_db_connection()

    if search:
        cores = connection.execute(
            """
            SELECT *
            FROM cores
            WHERE name LIKE ?
               OR grade LIKE ?
               OR effect LIKE ?
               OR obtain_location LIKE ?
               OR description LIKE ?
            ORDER BY id DESC
            """,
            (
                f"%{search}%",
                f"%{search}%",
                f"%{search}%",
                f"%{search}%",
                f"%{search}%",
            ),
        ).fetchall()
    else:
        cores = connection.execute(
            """
            SELECT *
            FROM cores
            ORDER BY id DESC
            """
        ).fetchall()

    total_quantity_row = connection.execute(
        """
        SELECT COALESCE(SUM(quantity), 0) AS total_quantity
        FROM cores
        """
    ).fetchone()

    total_quantity = total_quantity_row["total_quantity"]

    connection.close()

    return render_template(
        "support.html",
        cores=cores,
        search=search,
        total_quantity=total_quantity,
    )


@app.route("/support/hidden-jobs")
def support_hidden_jobs():
    search = request.args.get(
        "search",
        "",
    ).strip()

    connection = get_db_connection()

    if search:
        hidden_jobs = connection.execute(
            """
            SELECT *
            FROM hidden_jobs
            WHERE name LIKE ?
               OR category LIKE ?
               OR conditions LIKE ?
               OR prerequisite_quest LIKE ?
               OR npc_name LIKE ?
               OR npc_coordinates LIKE ?
               OR description LIKE ?
            ORDER BY id DESC
            """,
            (
                f"%{search}%",
                f"%{search}%",
                f"%{search}%",
                f"%{search}%",
                f"%{search}%",
                f"%{search}%",
                f"%{search}%",
            ),
        ).fetchall()
    else:
        hidden_jobs = connection.execute(
            """
            SELECT *
            FROM hidden_jobs
            ORDER BY id DESC
            """
        ).fetchall()

    connection.close()

    return render_template(
        "support_hidden_jobs.html",
        hidden_jobs=hidden_jobs,
        search=search,
    )


# =========================================================
# 파일 크기 오류
# =========================================================

@app.errorhandler(413)
def file_too_large(_error):
    flash(
        "이미지 크기는 최대 5MB까지 등록할 수 있습니다.",
        "error",
    )

    return redirect(
        request.referrer
        or url_for("core_list")
    )


# =========================================================
# 실행
# =========================================================

import os

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)