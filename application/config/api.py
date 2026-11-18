from ninja import NinjaAPI

from billing.api import router as billing_router
from core.auth import ApiAuth
from core.errors import register_error_handlers
from defects.api import router as defects_router
from organizations.api import router as organizations_router
from plans.api import router as plans_router
from projects.api import router as projects_router
from reports.api import router as reports_router
from users.api import router as auth_router

api = NinjaAPI(title='Usterki na planie API', version='1.0.0', auth=ApiAuth(), urls_namespace='api')
register_error_handlers(api)

api.add_router('/auth/', auth_router, tags=['auth'])
api.add_router('/organization/', organizations_router, tags=['organization'])
api.add_router('/projects/', projects_router, tags=['projects'])
api.add_router('/', plans_router, tags=['plans'])
api.add_router('/', defects_router, tags=['defects'])
api.add_router('/', reports_router, tags=['reports'])
api.add_router('/billing/', billing_router, tags=['billing'])
