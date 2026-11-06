"""Public local contracts only; never a substitute for authenticated provider tests."""
import asyncio
import httpx
from app.api import server
from app.automation.provider_catalog import public_catalog,selection

def test_all_seven_model_choices_stable_and_api_options_do_not_dispatch():
    catalog=public_catalog()
    assert [x['value'] for x in catalog['options']]==[
        'chatgpt','gemini','deepseek','ollama','chatgpt:api','gemini:api','deepseek:api']
    assert catalog['default']=='chatgpt'
    for choice in catalog['options'][-3:]:
        assert choice['transport']=='api' and choice['available'] is False
        try:selection(choice['value'],'api')
        except ValueError as exc:assert 'not configured' in str(exc).lower()
        else:raise AssertionError('Unconfigured API choice unexpectedly accepted')

def test_public_api_rejection_has_no_task_side_effect_and_no_secret_echo():
    async def run():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=server.app),base_url='http://testserver') as http:
            headers={'X-Exodia-Client':'exodia-dashboard'}
            before=await http.get('/api/command/tasks')
            assert before.status_code==200
            count=len(before.json()['tasks'])
            for provider in ('chatgpt:api','gemini:api','deepseek:api'):
                r=await http.post('/api/command/tasks',headers=headers,json={
                    'agent_id':'kiko','model_choice':provider,'transport':'api',
                    'prompt':'Do not send an unconfigured test',
                    'custom_instructions':'PRIVATE_CONTRACT_SENTINEL'} )
                assert r.status_code==422
                assert 'not configured' in r.text.lower()
                assert 'PRIVATE_CONTRACT_SENTINEL' not in r.text
            after=await http.get('/api/command/tasks')
            assert after.status_code==200 and len(after.json()['tasks'])==count
    asyncio.run(run())
