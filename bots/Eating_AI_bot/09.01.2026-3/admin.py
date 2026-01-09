from fastapi import FastAPI, Request, Form, Depends, HTTPException
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from sqlalchemy.orm import Session
from database.base import SessionLocal, engine, Base
from database.models import Block, BotUser, Trace, UserSession, UserParam
import uvicorn
import re
import os

# Create tables if not exist (for new columns/tables)
Base.metadata.create_all(bind=engine)

app = FastAPI()

# Setup Templates
templates_dir = os.path.join(os.path.dirname(__file__), "templates")
if not os.path.exists(templates_dir):
    os.makedirs(templates_dir)
templates = Jinja2Templates(directory=templates_dir)

# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

# --- USERS ---
@app.get("/users", response_class=HTMLResponse)
async def list_users(request: Request, q: str = None, db: Session = Depends(get_db)):
    query = db.query(BotUser)
    if q:
        search = f"%{q}%"
        query = query.filter(
            (BotUser.user_id.like(search)) | 
            (BotUser.username.like(search)) | 
            (BotUser.platform.like(search))
        )
    users = query.all()
    return templates.TemplateResponse("users.html", {"request": request, "users": users, "q": q})

@app.post("/users/create")
async def create_user(user_id: str = Form(...), username: str = Form(None), platform: str = Form(...), db: Session = Depends(get_db)):
    user = BotUser(user_id=user_id, username=username, platform=platform, is_active=True)
    db.add(user)
    db.commit()
    return RedirectResponse(url="/users", status_code=303)

@app.post("/users/{id}/toggle")
async def toggle_user(id: int, db: Session = Depends(get_db)):
    user = db.query(BotUser).filter(BotUser.id == id).first()
    if user:
        user.is_active = not user.is_active
        db.commit()
    return RedirectResponse(url="/users", status_code=303)

@app.post("/users/{id}/delete")
async def delete_user(id: int, db: Session = Depends(get_db)):
    user = db.query(BotUser).filter(BotUser.id == id).first()
    if user:
        db.delete(user)
        db.commit()
    return RedirectResponse(url="/users", status_code=303)

# --- WORKFLOW EDITOR ---
@app.get("/workflow", response_class=HTMLResponse)
async def workflow_editor(request: Request):
    return templates.TemplateResponse("editor.html", {"request": request})

@app.get("/api/graph")
async def get_graph(db: Session = Depends(get_db)):
    blocks = db.query(Block).all()
    nodes = []
    edges = []
    
    for b in blocks:
        nodes.append({
            "data": {"id": str(b.id), "name": b.name, "is_start": b.is_start},
            "position": {"x": b.ui_x, "y": b.ui_y}
        })
        
        # Parse script for go_to(ID)
        # Regex to find go_to(123)
        matches = re.findall(r"go_to\((\d+)\)", b.script_code)
        for target_id in matches:
            edges.append({
                "data": {
                    "source": str(b.id),
                    "target": str(target_id)
                }
            })
            
    return {"nodes": nodes, "edges": edges}

@app.post("/api/blocks/{id}/position")
async def update_position(id: int, x: float = Form(...), y: float = Form(...), db: Session = Depends(get_db)):
    block = db.query(Block).filter(Block.id == id).first()
    if block:
        block.ui_x = int(x)
        block.ui_y = int(y)
        db.commit()
    return {"status": "ok"}

@app.get("/api/blocks/{id}")
async def get_block(id: int, db: Session = Depends(get_db)):
    block = db.query(Block).filter(Block.id == id).first()
    if not block:
        raise HTTPException(status_code=404, detail="Block not found")
    return {"id": block.id, "name": block.name, "script_code": block.script_code}

@app.post("/api/blocks/{id}/save")
async def save_block(id: int, script_code: str = Form(...), name: str = Form(...), db: Session = Depends(get_db)):
    block = db.query(Block).filter(Block.id == id).first()
    if block:
        block.script_code = script_code
        block.name = name
        db.commit()
    return {"status": "ok"}

@app.post("/api/blocks/create")
async def create_block(name: str = Form("New Block"), x: int = Form(0), y: int = Form(0), db: Session = Depends(get_db)):
    # Find next available ID
    last_block = db.query(Block).order_by(Block.id.desc()).first()
    new_id = (last_block.id + 1) if last_block else 1
    
    new_block = Block(
        id=new_id,
        name=f"{name} {new_id}",
        script_code="\nif event == 'enter':\n    send_message('New Block')\n",
        ui_x=x,
        ui_y=y
    )
    db.add(new_block)
    db.commit()
    return {"id": new_block.id, "name": new_block.name, "script_code": new_block.script_code, "ui_x": new_block.ui_x, "ui_y": new_block.ui_y}

@app.post("/api/blocks/{id}/delete")
async def delete_block(id: int, db: Session = Depends(get_db)):
    block = db.query(Block).filter(Block.id == id).first()
    if block:
        db.delete(block)
        db.commit()
    return {"status": "ok"}

@app.post("/api/validate_code")
async def validate_code(script_code: str = Form(...)):
    # Mock context
    output_log = []
    def mock_send_message(
    text,
    buttons=None,
    parse_mode="text",
    request_contact=False):
        output_log.append(
        f"send_message: text='{text}', "
        f"buttons={buttons}, "
        f"parse_mode={parse_mode}, "
        f"request_contact={request_contact}")
        
    #def mock_send_message(text, buttons=None):
    #    output_log.append(f"send_message: {text} (Buttons: {buttons})")
    
    def mock_set_param(key, value):
        output_log.append(f"set_param: {key} = {value}")
        
    def mock_get_param(key):
        return "mock_value"
        
    def mock_go_to(block_id):
        output_log.append(f"go_to: {block_id}")
        
    def mock_module_start(name):
        output_log.append(f"ModuleStart: {name}")

    def mock_call_module(name, func, *args):
        return f"Mock result from {name}.{func}"

    context = {
        'input_text': 'test_input',
        'event': 'message',
        'set_param': mock_set_param,
        'get_param': mock_get_param,
        'send_message': mock_send_message,
        'go_to': mock_go_to,
        'ModuleStart': mock_module_start,
        'call_module': mock_call_module,
        'print': lambda *args: output_log.append(" ".join(map(str, args)))
    }
    
    try:
        exec(script_code, context)
        return {"status": "ok", "output": "\n".join(output_log)}
    except Exception as e:
        import traceback
        tb = traceback.extract_tb(e.__traceback__)
        # Find the line number in the script (not the wrapper)
        line_no = -1
        for frame in tb:
            if frame.filename == "<string>":
                line_no = frame.lineno
                break
        
        return {"status": "error", "message": str(e), "line": line_no}

@app.post("/api/format_code")
async def format_code(script_code: str = Form(...)):
    try:
        import black
        formatted = black.format_str(script_code, mode=black.Mode())
        return {"status": "ok", "formatted_code": formatted}
    except Exception as e:
        return {"status": "error", "message": str(e)}

# --- TRACE ---
@app.get("/trace", response_class=HTMLResponse)
async def view_trace(request: Request, user_id: str = None, q: str = None, db: Session = Depends(get_db)):
    # Get all users who have sessions, optionally filtered
    session_query = db.query(UserSession)
    
    if q:
        # Join with BotUser to search by username
        # Note: This assumes UserSession.user_id matches BotUser.user_id. 
        # Ideally we should have a relationship, but for now we can filter manually or join.
        # Let's try a simple join if possible, or just filter by user_id if no relationship.
        # Given the models, UserSession doesn't have a direct relationship to BotUser defined in models.py shown earlier.
        # So we'll filter by user_id or platform on UserSession, and if possible filter by username via subquery or join.
        # For simplicity and speed, let's fetch all and filter in python or do a join if we add it.
        # Let's do a join with BotUser.
        session_query = session_query.outerjoin(BotUser, (UserSession.user_id == BotUser.user_id) & (UserSession.platform == BotUser.platform))
        search = f"%{q}%"
        session_query = session_query.filter(
            (UserSession.user_id.like(search)) |
            (BotUser.username.like(search)) |
            (UserSession.platform.like(search))
        )
    
    sessions = session_query.all()
    
    # Pre-fetch user info for display (username)
    # We can create a map of user_id -> username
    user_map = {}
    bot_users = db.query(BotUser).all()
    for bu in bot_users:
        user_map[bu.user_id] = bu.username

    selected_user_data = None
    traces = []
    
    if user_id:
        # Get specific session info
        user_session = db.query(UserSession).filter(UserSession.user_id == user_id).first()
        params = db.query(UserParam).filter(UserParam.user_id == user_id).all()
        traces = db.query(Trace).filter(Trace.user_id == user_id).order_by(Trace.created_at.desc()).limit(100).all()
        
        # Get all blocks for the dropdown
        all_blocks = db.query(Block).all()
        
        selected_user_data = {
            "session": user_session,
            "params": params,
            "blocks": all_blocks,
            "username": user_map.get(user_id)
        }
    else:
        # Just show recent traces if no user selected
        traces = db.query(Trace).order_by(Trace.created_at.desc()).limit(100).all()

    return templates.TemplateResponse("trace.html", {
        "request": request, 
        "sessions": sessions, 
        "user_map": user_map,
        "selected_user_id": user_id,
        "selected_data": selected_user_data,
        "traces": traces,
        "q": q
    })

@app.post("/api/session/{user_id}/block")
async def update_session_block(user_id: str, block_id: int = Form(...), db: Session = Depends(get_db)):
    session = db.query(UserSession).filter(UserSession.user_id == user_id).first()
    if session:
        session.current_block_id = block_id
        db.commit()
    return RedirectResponse(url=f"/trace?user_id={user_id}", status_code=303)





if __name__ == "__main__":
    admin_ip = os.getenv("ADMIN_IP")
    if not admin_ip:
        print("Error: ADMIN_IP not found in .env")
        admin_ip = "127.0.0.1"

    admin_port_def = 8005 
    admin_port = os.getenv("ADMIN_PORT")
    if not admin_port:
        print("Error: ADMIN_IP not found in .env")
        admin_port = admin_port_def
    else:
        # Преобразуем строку в число
        try:
            admin_port = int(admin_port)
        except ValueError:
            print(f"Error: ADMIN_PORT must be a number, got '{admin_port}'")
            admin_port = admin_port_def
    uvicorn.run(app, host=admin_ip, port=admin_port)
