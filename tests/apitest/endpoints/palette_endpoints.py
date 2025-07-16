"""
Palette Control Endpoints
"""
from fastapi import APIRouter, HTTPException, Path, Body, Request
from dataclass.api_models import ChangePaletteRequest, PaletteColorRequest, OSCApiResponse
from dataclass.osc_models import OSCRequest, OSCMessageType, OSCDataType
from services.osc_client import OSCClientContext, UDPOSCClient
from services.message_factory import message_factory
from services.language_service import language_service, get_request_language

router = APIRouter()

osc_client = OSCClientContext(UDPOSCClient())

@router.post("/change_palette", response_model=OSCApiResponse)
async def change_palette(request: ChangePaletteRequest, http_request: Request):
    try:
        osc_request = OSCRequest()
        osc_request.set_address("/change_palette")
        osc_request.set_message_type(OSCMessageType.LED_CONTROL)
        osc_request.add_parameter("palette_id", request.palette_id, OSCDataType.INT, "Palette ID")
        
        response = await osc_client.send_message(osc_request)
        
        # Get localized message
        lang = get_request_language(http_request)
        log_message = language_service.get_response_message(
            "palette_changed", 
            language=lang,
            palette_id=request.palette_id
        )
        
        return OSCApiResponse(
            success=response.is_success(),
            message=log_message,
            data={
                "palette_id": request.palette_id,
                "osc_response": response.__dict__
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/palette/{palette_id}/{color_id}", response_model=OSCApiResponse)
async def update_palette_color(
    palette_id: int = Path(..., description="Palette ID (0-origin)"),
    color_id: int = Path(..., description="Color ID (0-5)"),
    request: PaletteColorRequest = Body(...),
    http_request: Request = None
):
    try:
        osc_request = message_factory.create_palette_message(
            palette_id=palette_id,
            color_id=color_id,
            r=request.r,
            g=request.g,
            b=request.b
        )
        
        response = await osc_client.send_message(osc_request)
        
        # Get localized message
        lang = get_request_language(http_request)
        log_message = language_service.get_response_message(
            "palette_color_updated", 
            language=lang,
            palette_id=palette_id,
            color_id=color_id,
            r=request.r,
            g=request.g,
            b=request.b
        )
        
        return OSCApiResponse(
            success=response.is_success(),
            message=log_message,
            data={
                "palette_id": palette_id,
                "color_id": color_id,
                "rgb": [request.r, request.g, request.b],
                "osc_response": response.__dict__
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 