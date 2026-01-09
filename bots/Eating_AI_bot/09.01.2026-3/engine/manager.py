import importlib.util
import os
import sys
from sqlalchemy.orm import Session
from database.models import Module

class ModuleManager:
    def __init__(self, db_session_factory):
        self.db_session_factory = db_session_factory
        self.loaded_modules = {} # name -> module instance/object

    def load_module(self, name: str):
        db = self.db_session_factory()
        try:
            module_record = db.query(Module).filter_by(name=name).first()
            if not module_record:
                raise ValueError(f"Module {name} not found in database")

            file_path = module_record.py_file
            if not os.path.exists(file_path):
                # Try relative to project root if not absolute
                # Assuming MOD folder is in project root
                file_path = os.path.abspath(file_path)
                if not os.path.exists(file_path):
                     raise FileNotFoundError(f"Module file not found: {file_path}")

            spec = importlib.util.spec_from_file_location(name, file_path)
            if spec is None:
                raise ImportError(f"Could not load spec for module {name}")
            
            module = importlib.util.module_from_spec(spec)
            sys.modules[name] = module
            spec.loader.exec_module(module)
            
            # Instantiate the main class if convention exists, or just return module
            # The user example has a class GigaChatAssistant.
            # We might need a convention. For now, let's assume the module exposes a specific class or function?
            # Or we just return the module object and let the script call what it needs.
            # But the user said "Initialization... at first call".
            # Let's assume the module has an `init()` function or we just return the module.
            
            self.loaded_modules[name] = module
            
            module_record.status = "run"
            db.commit()
            print(f"Module {name} loaded successfully.")
            return module

        except Exception as e:
            print(f"Error loading module {name}: {e}")
            if module_record:
                module_record.status = "error"
                db.commit()
            raise e
        finally:
            db.close()

    def get_module(self, name: str):
        if name in self.loaded_modules:
            return self.loaded_modules[name]
        return self.load_module(name)
