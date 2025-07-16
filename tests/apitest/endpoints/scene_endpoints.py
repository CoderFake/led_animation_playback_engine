"""
Scene Management Endpoints
"""
from fastapi import APIRouter, HTTPException, Request
from dataclass.api_models import LoadJsonRequest, ChangeSceneRequest, OSCApiResponse
from dataclass.osc_models import OSCRequest, OSCMessageType, OSCDataType
from services.osc_client import OSCClientContext, UDPOSCClient
from services.language_service import language_service, get_request_language

router = APIRouter()

osc_client = OSCClientContext(UDPOSCClient())

@router.post("/load_json", response_model=OSCApiResponse)
async def load_json(request: LoadJsonRequest, http_request: Request):
    try:
        osc_request = OSCRequest()
        osc_request.set_address("/load_json")
        osc_request.set_message_type(OSCMessageType.LED_CONTROL)
        osc_request.add_parameter("file_path", request.file_path, OSCDataType.STRING, "JSON file path")
     
        response = await osc_client.send_message(osc_request)
        
        # Get localized message
        lang = get_request_language(http_request)
        log_message = language_service.get_response_message(
            "scene_loaded", 
            language=lang,
            file_path=request.file_path
        )
        
        return OSCApiResponse(
            success=response.is_success(),
            message=log_message,
            data={
                "file_path": request.file_path,
                "osc_response": response.__dict__
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/change_scene", response_model=OSCApiResponse)
async def change_scene(request: ChangeSceneRequest, http_request: Request):
    try:
        osc_request = OSCRequest()
        osc_request.set_address("/change_scene")
        osc_request.set_message_type(OSCMessageType.LED_CONTROL)
        osc_request.add_parameter("scene_id", request.scene_id, OSCDataType.INT, "Scene ID")
        
        response = await osc_client.send_message(osc_request)
        
        # Get localized message
        lang = get_request_language(http_request)
        log_message = language_service.get_response_message(
            "scene_changed", 
            language=lang,
            scene_id=request.scene_id
        )
        
        return OSCApiResponse(
            success=response.is_success(),
            message=log_message,
            data={
                "scene_id": request.scene_id,
                "osc_response": response.__dict__
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 