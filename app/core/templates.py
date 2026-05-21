"""
Configuration centralisée de Jinja2.
Tous les routers HTML utiliseront cette instance unique.
"""
from fastapi.templating import Jinja2Templates

templates = Jinja2Templates(directory="app/templates")