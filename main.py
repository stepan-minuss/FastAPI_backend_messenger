from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import os
from sqladmin import Admin
import socketio
import logging
from database import engine, init_db
from admin import UserAdmin, MessageAdmin
from routes import router
from socketio_handler import ChatNamespace

    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
        ]
    )
app = FastAPI(
    title="Messenger Backend API",
    description="Backend API for messenger application with E2EE support",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

init_db()

app.include_router(router)

os.makedirs("static/avatars", exist_ok=True)
os.makedirs("static/uploads", exist_ok=True)

app.mount("/static", StaticFiles(directory="static"), name="static")
admin = Admin(
    app, 
    engine, 
    title="Nebula Admin Panel",
    base_url="/admin",
    logo_url="https://via.placeholder.com/200x50/7C4DFF/FFFFFF?text=Nebula+Admin",
    templates_dir="templates",
)
admin.add_view(UserAdmin)
admin.add_view(MessageAdmin)

sio = socketio.AsyncServer(
    async_mode='asgi',
    cors_allowed_origins="*",
    logger=True,
    engineio_logger=True,
    ping_timeout=60,
    ping_interval=25,
    max_http_buffer_size=1e6,
    allow_upgrades=True,
    transports=['polling', 'websocket'],
)
sio.register_namespace(ChatNamespace('/'))

from socketio_handler import set_sio_server
set_sio_server(sio)

socketio_app = socketio.ASGIApp(sio, other_asgi_app=app, socketio_path='socket.io')

@app.get("/")
async def root():
    return {
        "message": "Messenger Backend API",
        "docs": "/docs",
        "admin": "/admin"
    }


@app.get("/health")
async def health():
    return {"status": "healthy"}


asgi_app = socketio_app

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(socketio_app, host="0.0.0.0", port=5000)

