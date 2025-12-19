from json import load
from unicodedata import category
from flask import Flask, flash, render_template, request, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from werkzeug.utils import secure_filename
import os 
from dotenv import load_dotenv

load_dotenv()
VALID_USER = os.getenv("BLOG_USER", "admin") #valor por defecto
VALID_PASS = os.getenv("BLOG_PASS", "1234")
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'static', 'uploads')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

app = Flask(__name__)
app.config['SECRET_KEY'] = 'tu-clave-secreta-aqui-cambiala-por-una-segura'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Configuración de la base de datos SQLite
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///blog.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Modelo de Post
class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    content = db.Column(db.Text, nullable=False)
    image_url = db.Column(db.String(200))
    category = db.Column(db.String(50)) #nueva columna

    tags = db.Column(db.String(200)) #aqui guardaremos etiquetas separadas por coma
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
# Crear tablas  
with app.app_context():
    db.create_all()

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        #VALIDACIÓN CON VARIABLES DE ENTORNO
        if username == VALID_USER and password == VALID_PASS:
            session["user"] = username
            flash("Inicio de sesión exitoso", "success")
            return redirect(url_for("home"))
        else:
            flash("Credenciales inválidas", "error")

    return render_template("login.html")

@app.route("/logout")
def logout():
    session.pop("user", None)
    flash("Has cerrado sesión", "info")
    return redirect(url_for("home"))

@app.route("/")
def home():
    posts = Post.query.all()
    return render_template("home.html", posts=posts, demo_user=VALID_USER, demo_pass=VALID_PASS)

@app.route("/add", methods=["GET", "POST"])
def add():
    if "user" not in session:
        flash("Debes iniciar sesión para agregar post", "error")
        return redirect(url_for("login"))

    if request.method == "POST":
        title = request.form.get("title", "").strip()
        content = request.form.get("content", "").strip()
        image_file = request.files.get("image")  # ← Aquí tomamos la imagen
        image_filename = None  # ← Variable para guardar el nombre del archivo
        category = request.form.get("category", "").strip()
        tags = request.form.get("tags", "").strip()
        # Validación de campos
        if not title or not content:
            error = "Todos los campos son obligatorios"
            return render_template("add.html", error=error)

        # Si hay imagen y es válida
        if image_file and image_file.filename and allowed_file(image_file.filename):
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_')
            filename = timestamp + secure_filename(image_file.filename)
            image_file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            image_filename = filename
        # Crear el post con imagen (si existe)
        new_post = Post(title=title, content=content, image_url=image_filename, category=category if category else None, tags=tags if tags else None)
        db.session.add(new_post)
        db.session.commit()
        flash("Post agregado con éxito", "success")
        return redirect(url_for("home"))

    return render_template("add.html")

@app.route("/delete/<int:id>")
def delete(id):
    if "user" not in session:
        flash("Debes iniciar sesión para eliminar post", "error")
        return redirect(url_for("login"))
    post = Post.query.get_or_404(id)   #busca el post por id
    if post.image_url:
        image_path = os.path.join(app.config['UPLOAD_FOLDER'], post.image_url)
        if os.path.exists(image_path):
            os.remove(image_path)
    db.session.delete(post)   #lo elimina de la base de datos
    db.session.commit()  #guarda los cambios
    return redirect(url_for("home"))   #vuelve a la página principal

@app.route("/edit/<int:id>", methods=["GET", "POST"])
def edit(id):
    if "user" not in session:
        flash("Debes iniciar sesión para editar el post", "error")
        return redirect(url_for("login"))
    post = Post.query.get_or_404(id)  #post = Post.query.get_or_404(id)
    if request.method == "POST":
        # Capturamos los datos del formulario y eliminamos espacios vacíos
        title = request.form.get("title", "").strip()
        content = request.form.get("content", "").strip()
        category = request.form.get("category", "").strip()
        tags = request.form.get("tags", "").strip()
        image_file = request.files.get("image")
        #validamos que los campos no esten vacíos.

        if not title or not content:
            error = "Todos los campos son obligatorios"
            return render_template("edit.html", post=post, error=error)
            #si todo está bien, actualizamos el post
        
        if image_file and image_file.filename and allowed_file(image_file.filename):
            if post.image_url:
                #si ya existe una imagen, la eliminamos
                #obtenemos la ruta de la imagen
                old_path = os.path.join(app.config['UPLOAD_FOLDER'], post.image_url)
                if os.path.exists(old_path):
                    os.remove(old_path)  #la eliminamos
            #guarda la nueva imagen
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_')
            filename = timestamp + secure_filename(image_file.filename)
            image_file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            post.image_url = filename  #guardamos el nombre de la nueva imagen
        
        post.title = title
        post.content = content
        post.category = category if category else None
        post.tags = tags if tags else None
        db.session.commit()
        return redirect(url_for("home"))
        #Si es get, siempre mostramos el formulario
    return render_template("edit.html", post=post)

@app.route("/post/<int:id>")
def post_detail(id):
    post = Post.query.get_or_404(id)
    return render_template("post_detail.html", post=post)

@app.route("/search")
def search():
    query = request.args.get("q", "").strip()
    if not query: 
        return redirect(url_for("home"))

    from sqlalchemy import func
    
    query_lower = query.lower()
    # CORREGIDO: Manejar campos None correctamente
    conditions = [
        func.lower(Post.title).like(f"%{query_lower}%"),
        func.lower(Post.content).like(f"%{query_lower}%")
    ]
    
    # Solo agregar condiciones si los campos pueden tener valores
    conditions.append(func.lower(Post.category).like(f"%{query_lower}%"))
    conditions.append(func.lower(Post.tags).like(f"%{query_lower}%"))
    
    results = Post.query.filter(db.or_(*conditions)).all()
    return render_template("search_results.html", results=results, query=query)

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)




