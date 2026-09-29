"""Generate the checked-in OpenAPI contract; no runtime code generation."""
import json
from pathlib import Path

def obj(props, required=()):
    return {"type":"object", "properties":props, "required":list(required), "additionalProperties":False}
def num(lo,hi): return {"type":"integer","minimum":lo,"maximum":hi}
def ref(name): return {"$ref":"#/components/schemas/"+name}
def hx(lo,hi,pattern="^(?:[0-9A-Fa-f]{2})+$"):
    return {"type":"string","minLength":lo,"maxLength":hi,"pattern":pattern}
boolean={"type":"boolean"}
selector=obj({"bank":num(1,3),"bit_address":num(0,16383),"hex":hx(2,62)},("bank","bit_address","hex"))
selector["description"]="Whole-byte mask, max 248 bits; bit_address + mask bits <= 16384. May match multiple tags."
common={"antenna":num(1,4),"bank":num(0,3),"word_address":num(0,65535),"selector":ref("Selector"),"password":{**hx(8,8),"default":"00000000"}}
read=obj({**common,"words":num(1,120)},("antenna","bank","word_address","words","selector"))
write=obj({**common,"bank":{"type":"integer","enum":[1,3]},"hex":hx(4,128,"^(?:[0-9A-Fa-f]{4})+$")},("antenna","bank","word_address","hex","selector"))
write["description"]="1..32 words; EPC CRC word 0 forbidden; range cannot wrap. PC is not auto-adjusted. No automatic retries or readback."
inv=obj({"antennas":{"type":"array","minItems":1,"maxItems":4,"uniqueItems":True,"items":num(1,4)},"scan_time":{**num(3,20),"default":3,"description":"100 ms units per antenna"},"q":{**num(0,15),"default":4},"session":{**num(0,3),"default":0},"target":{**num(0,1),"default":0},"selector":ref("Selector")})
schemas={"Selector":selector,"ReadRequest":read,"WriteRequest":write,"InventoryRequest":inv,
"QueryRequest":{**obj({"q":num(0,15),"session":{"type":"integer","enum":[0,1,2,3,255]},"persist":{**boolean,"default":False}}),"anyOf":[{"required":["q"]},{"required":["session"]}],"description":"Native Ex10 CFG9 for fast query. Partial updates preserve the other field; persist saves both fields. Does not change ordinary inventory per-call defaults."},
"Query":obj({"q":num(0,15),"session":{"type":"integer","enum":[0,1,2,3,255]},"simulated":boolean},("q","session","simulated")),
"PowerRequest":{**obj({"dbm":num(0,30),"powers_dbm":{"type":"array","minItems":1,"maxItems":4,"items":num(0,30),"description":"Exactly one value per configured antenna, in ANT1..ANT4 order"},"persist":{**boolean,"default":False}}),"oneOf":[{"required":["dbm"],"not":{"required":["powers_dbm"]}},{"required":["powers_dbm"],"not":{"required":["dbm"]}}]},
"RegionRequest":obj({"band":num(0,255),"min_channel":num(0,255),"max_channel":num(0,255),"persist":{**boolean,"default":False}},("band","min_channel","max_channel")),
"Region":obj({"band":num(0,255),"min_channel":num(0,255),"max_channel":num(0,255),"band_name":{"type":["string","null"]},"table_known":boolean,"frequencies_khz":{"type":["array","null"],"items":{"type":"integer"}},"simulated":boolean},("band","min_channel","max_channel","band_name","table_known","frequencies_khz","simulated")),
"ProfileRequest":obj({"profile_id":num(0,65535),"format":{"type":"string","enum":["auto","legacy","extended"],"default":"auto","description":"auto prefers extended reads and falls back to legacy only after explicit FD/FE device rejection. legacy IDs 0..63; extended 0..65535. Raw ZK namespace, not Nation mode IDs."},"persist":{**boolean,"default":False}},("profile_id",)),
"Profile":obj({"profile_id":num(0,65535),"format":{"type":"string","enum":["legacy","extended"]},"namespace":{"type":"string","enum":["zk"]},"simulated":boolean},("profile_id","format","namespace","simulated")),
"Health":obj({"version":{"type":"string"},"simulated":boolean,"connected":boolean},("version","simulated","connected")),
"ReaderInfo":obj({"simulated":boolean,"address":num(0,254),"firmware":{"type":"string"},"reader_type":num(0,255),"protocol_bits":num(0,255),"configured_antennas":{"type":"integer","enum":[1,4]},"power_dbm":num(0,255),"antenna_mask":num(0,15),"frequency_bytes":hx(4,4),"check_antenna":num(0,255)},("simulated","address","firmware","reader_type","protocol_bits","configured_antennas","power_dbm","antenna_mask","frequency_bytes","check_antenna")),
"Power":obj({"dbm":{"type":["integer","null"],"minimum":0,"maximum":30,"description":"null when antenna values differ"},"powers_dbm":{"type":"array","minItems":1,"maxItems":4,"items":num(0,30)},"scope":{"type":"string","enum":["global","per_antenna"]},"simulated":boolean},("dbm","powers_dbm","scope","simulated")),
"Inventory":obj({"tags":{"type":"array","items":obj({"epc":hx(4,124),"antenna":num(1,4),"rssi_raw":num(0,255)},("epc","antenna","rssi_raw"))},"rounds":{"type":"array","items":obj({"antenna":num(1,4),"status":{"type":"integer","enum":[1,2,4,251]},"partial":boolean},("antenna","status","partial"))},"simulated":boolean},("tags","rounds","simulated")),
"ReadResult":obj({"hex":hx(4,480),"words":num(1,120),"simulated":boolean},("hex","words","simulated")),
"WriteResult":obj({"acknowledged":{"const":True,"type":"boolean"},"verified":{"const":False,"type":"boolean"},"words":num(1,32),"simulated":boolean},("acknowledged","verified","words","simulated")),
"Error":{"type":"object","required":["error"],"properties":{"error":{"type":"string"},"message":{"type":"string"},"command":num(0,255),"status":num(0,255),"detail_hex":{"type":"string"},"action_succeeded":boolean,"retry_safe":boolean}}}
paths={}
for path,method,operation,summary,request,result in [
('/health','get','health','Process/transport state, no device I/O',None,'Health'),
('/v1/reader','get','readerInfo','Read module information',None,'ReaderInfo'),
('/v1/power','get','getPower','Read each antenna power from hardware',None,'Power'),
('/v1/power','post','setPower','Set global or individual antenna powers and read back','PowerRequest','Power'),
('/v1/region','get','getRegion','Read band and operating channel range',None,'Region'),
('/v1/region','post','setRegion','Set band/channel range or fixed channel and read back','RegionRequest','Region'),
('/v1/profile','get','getProfile','Read actual ZK link profile; prefer extended, explicit-error legacy fallback',None,'Profile'),
('/v1/profile/extended','get','getExtendedProfile','Read ZK extended link profile',None,'Profile'),
('/v1/profile','post','setProfile','Set raw ZK profile ID and read back','ProfileRequest','Profile'),
('/v1/query','get','getQuery','Read native Ex10 CFG9 Q/Session',None,'Query'),
('/v1/query','post','setQuery','Set native Q/Session, preserve omitted field and read back','QueryRequest','Query'),
('/v1/inventory','post','inventory','One finite scan per selected antenna','InventoryRequest','Inventory'),
('/v1/read','post','readMemory','Read selected tag memory','ReadRequest','ReadResult'),
('/v1/write','post','writeMemory','Write EPC/User once; no readback or retry','WriteRequest','WriteResult')]:
    responses={"200":{"description":"Success; inspect simulated, partial or verified fields","content":{"application/json":{"schema":ref(result)}}}}
    for status,description in [(400,'Invalid input'),(401,'Missing/invalid Bearer token'),(403,'Host or Origin rejected'),(409,'Reader busy'),(411,'Content-Length required'),(413,'Body exceeds 8192 bytes'),(415,'JSON content type required'),(422,'Device error; raw status preserved'),(502,'Protocol/restore error; a write may already have occurred'),(503,'Transport unavailable; close/reopen, do not retry writes blindly')]:
        responses[str(status)]={"description":description,"content":{"application/json":{"schema":ref('Error')}}}
    item={"operationId":operation,"summary":summary,"responses":responses}
    if request:item['requestBody']={"required":True,"content":{"application/json":{"schema":ref(request)}}}
    paths.setdefault(path,{})[method]=item
spec={"openapi":"3.1.0","info":{"title":"ZK Reader API","version":"0.1.0a3","description":"Local API for direct serial Ex10 reader access on the same OS. Power/region/profile set-get verified on one Windows-connected four-antenna module; macOS/Linux and RF read/write are not yet qualified. Poll inventory sequentially for continuous reading; no background start/stop. Never automatically retry a write."},"servers":[{"url":"http://127.0.0.1:8765"}],"security":[{"bearerAuth":[]}],"paths":paths,"components":{"securitySchemes":{"bearerAuth":{"type":"http","scheme":"bearer"}},"schemas":schemas}}
Path(__file__).resolve().parents[1].joinpath('docs/openapi.json').write_text(json.dumps(spec,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
