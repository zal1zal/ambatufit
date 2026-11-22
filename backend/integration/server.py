import asyncio
import hmac
import os
import uuid
from fastapi import FastAPI, Header, HTTPException, Query, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from app.config import settings
from app.security import decode_access_token
from integration.adapters.ambatunoutrish import AmbatuNoutrishAdapter
from integration.adapters.ambatumove import AmbatuMoveAdapter
from integration.schemas import FoodList, GymList, ProviderStatus

app = FastAPI(title='AmbatuFit Off-STB Integration Service', version='1.0.0')
app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origin_list, allow_methods=['GET'], allow_headers=['Authorization', 'X-Service-Token', 'X-Request-ID'], expose_headers=['X-Request-ID'])

noutrish_adapter = AmbatuNoutrishAdapter(settings.NUTRITION_PROVIDER_BASE_URL, settings.NUTRITION_PROVIDER_API_KEY)
ambatumove_adapter = AmbatuMoveAdapter(settings.GYM_PROVIDER_BASE_URL, settings.GYM_PROVIDER_API_KEY)


def authorize(authorization: str | None = Header(None), x_service_token: str | None = Header(None)):
    # Service secrets stay on servers. Mobile reuses its short-lived core JWT.
    if (x_service_token and settings.INTEGRATION_API_TOKEN and
            not settings.INTEGRATION_API_TOKEN.startswith('replace') and
            hmac.compare_digest(x_service_token, settings.INTEGRATION_API_TOKEN)):
        return
    scheme, _, token = (authorization or '').partition(' ')
    if scheme.lower() != 'bearer' or not decode_access_token(token):
        raise HTTPException(401, detail='Sesi tidak valid. Silakan masuk kembali.')


@app.middleware('http')
async def request_id(request: Request, call_next):
    request.state.request_id = f'req-{uuid.uuid4().hex[:12]}'
    response = await call_next(request)
    response.headers['X-Request-ID'] = request.state.request_id
    return response


@app.exception_handler(HTTPException)
async def http_error(request: Request, exc: HTTPException):
    return JSONResponse(status_code=exc.status_code, content={'error': {'code': 'UNAUTHORIZED' if exc.status_code == 401 else 'HTTP_ERROR', 'message': exc.detail, 'request_id': request.state.request_id}})


@app.exception_handler(RequestValidationError)
async def validation_error(request: Request, exc: RequestValidationError):
    return JSONResponse(status_code=422, content={'error': {'code': 'VALIDATION_ERROR', 'message': 'Parameter pencarian tidak valid.', 'request_id': request.state.request_id}})


@app.get('/health')
def health():
    return {'status': 'healthy', 'service': 'ambatufit-integration'}


@app.get('/integration/v1/status', response_model=dict[str, ProviderStatus], dependencies=[Depends(authorize)])
async def get_status():
    nutrition, gym = await asyncio.gather(noutrish_adapter.get_foods(), ambatumove_adapter.get_gyms())
    return {'ambatunoutrish': nutrition[1], 'ambatumove': gym[1]}


@app.get('/integration/v1/nutrition/foods', response_model=FoodList, dependencies=[Depends(authorize)])
async def get_nutrition_foods(query: str | None = Query(None, max_length=200)):
    items, provider_status = await noutrish_adapter.get_foods(query)
    return {'items': items, 'total': len(items), 'provider_status': provider_status}


@app.get('/integration/v1/fitness/gyms', response_model=GymList, dependencies=[Depends(authorize)])
async def get_fitness_gyms(city: str | None = Query(None, max_length=200)):
    items, provider_status = await ambatumove_adapter.get_gyms(city)
    return {'items': items, 'total': len(items), 'provider_status': provider_status}
