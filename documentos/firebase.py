import pyrebase
from django.contrib.auth import logout
from django.shortcuts import redirect

firebaseConfig = {
    "apiKey": "AIzaSyA4CvBsyeGZP3qbcv_mK-mRpjmWDB3p3Zk",
    "authDomain": "docenter-7484f.firebaseapp.com",
    "databaseURL": "https://docenter-7484f-default-rtdb.firebaseio.com",
    "projectId": "docenter-7484f",
    "storageBucket": "docenter-7484f.firebasestorage.app",
    "messagingSenderId": "80541482392",
    "appId": "1:80541482392:web:d2ee5bb92064358425bfed",
    "measurementId": "G-7LCEECJH0C"
}

# Inicializa Firebase
firebase = pyrebase.initialize_app(firebaseConfig)

# Conecta a Realtime Database
db = firebase.database()

# Conecta a Firebase Authentication
auth = firebase.auth()

# Conecta a Firebase Storage
storage = firebase.storage()


#busca usuario por correo
def obtener_usuario_por_correo(correo):
    usuarios = db.child("Usuarios").get().val()
    if usuarios:
        for uid, usuario in usuarios.items():
            if isinstance(usuario, dict) and usuario.get("correo") == correo:
                return uid, usuario
    return None, None