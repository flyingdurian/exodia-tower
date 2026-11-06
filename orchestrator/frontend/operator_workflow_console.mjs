import {AGENTS, safeWorkflow} from './operator_workflow_contract.mjs';
import {safeRecoveryFork} from './workflow_recovery_contract.mjs';
import {safeWorkflowEvidence} from './workflow_evidence_contract.mjs';

const byId = id => document.getElementById(id);
const stageEditors = byId('stepEditors');
const notice = byId('notice');
let selected = null;
let selectionRevision = 0;
const HEADER = {'X-Exodia-Client':'exodia-dashboard'};

function showNotice(message, error = false) {
  notice.textContent = message;
  notice.dataset.error = String(error);
}

async function request(path, options = {}) {
  const response = await fetch(path, {
    ...options,
    headers: {...HEADER, ...(options.headers || {})}
  });
  if (!response.ok) throw new Error('Local workflow service returned '+response.status);
  return response.json();
}

function addStage() {
  const index = stageEditors.children.length;
  if (index >= 12) return;
  const key = 's'+(index+1);
  const node = document.createElement('div');
  node.className = 'stage';
  node.dataset.stepKey = key;
  const head = document.createElement('div');
  head.className = 'stagehead';
  const title = document.createElement('strong');
  title.textContent = 'Stage '+(index+1);
  const tag = document.createElement('span');
  tag.className = 'tag';
  tag.textContent = key;
  head.append(title,tag);

  const fields = document.createElement('div');
  fields.className = 'stagefields';
  const label = document.createElement('label');
  label.textContent = 'Work item';
  const input = document.createElement('input');
  input.name = 'label';
  input.maxLength = 80;
  input.required = true;
  input.placeholder = 'Task objective for this companion';
  label.append(input);

  const agentLabel = document.createElement('label');
  agentLabel.textContent = 'Assigned companion';
  const agent = document.createElement('select');
  agent.name = 'agent_id';
  for (const [id,name] of AGENTS) {
    const option = document.createElement('option');
    option.value = id;
    option.textContent = name;
    agent.append(option);
  }
  agent.value = AGENTS[Math.min(index,AGENTS.length-1)][0];
  agentLabel.append(agent);
  fields.append(label,agentLabel);

  const deps = document.createElement('fieldset');
  const legend = document.createElement('legend');
  legend.textContent = 'Blocked until these earlier stages are answered';
  deps.append(legend);
  const choices = document.createElement('div');
  choices.className = 'dependencies';
  for (const previous of [...stageEditors.children]) {
    const choice = document.createElement('label');
    choice.className = 'checkline';
    const check = document.createElement('input');
    check.type = 'checkbox';
    check.value = previous.dataset.stepKey;
    check.checked = previous === stageEditors.lastElementChild;
    choice.append(check,document.createTextNode(previous.dataset.stepKey));
    choices.append(choice);
  }
  if (!index) {
    const none = document.createElement('span');
    none.className='muted';
    none.textContent='First stage has no prerequisites';
    choices.append(none);
  }
  deps.append(choices);
  node.append(head,fields,deps);
  stageEditors.append(node);
  byId('addStage').disabled=stageEditors.children.length>=12;
}

function compilePlan() {
  const title=byId('planTitle').value.trim();
  const steps=[...stageEditors.children].map(node=>({
    key:node.dataset.stepKey,
    label:node.querySelector('input[name=label]').value.trim(),
    agent_id:node.querySelector('select[name=agent_id]').value,
    depends_on:[...node.querySelectorAll('.dependencies input:checked')].map(x=>x.value)
  }));
  if (!title || steps.some(s=>!s.label)) throw new Error('Give every stage and plan a title');
  return {title,steps};
}

async function refreshPlans() {
  try {
    const response = await request('/api/command/workflows?limit=20');
    if (!response || response.schema!=='exodia.phase13.operator-workflow-list/v1' ||
        !Array.isArray(response.workflows)) throw new Error('Workflow list unavailable');
    const slot=byId('planList');
    slot.replaceChildren();
    if (!response.workflows.length) {
      const empty=document.createElement('p');
      empty.className='muted';
      empty.textContent='No saved operator workflows yet.';
      slot.append(empty);
    }
    for (const raw of response.workflows) {
      const plan=safeWorkflow(raw);
      const b=document.createElement('button');
      b.type='button';b.className='planbutton';
      b.textContent=plan.title+' · '+plan.completed+'/'+plan.stepCount+
        ' answered · '+(plan.status==='reviewed_local_only'?'Reviewed':'In progress');
      b.setAttribute('aria-current',String(selected?.id===plan.id));
      b.addEventListener('click',()=>{void selectPlan(plan.id);});
      slot.append(b);
    }
  } catch (_) {showNotice('Unable to read local workflow listing',true);}
}

function renderPlan(plan) {
  const area=byId('selectedPlan');
  area.replaceChildren();
  const title=document.createElement('h2');
  title.textContent=plan.title;
  const state=document.createElement('p');
  state.className='muted';
  state.textContent='Version '+plan.revision+' · '+plan.status.replaceAll('_',' ');
  area.append(title,state);
  const slot=byId('planSteps');
  slot.replaceChildren();

  const agents=new Map(AGENTS);
  for (const step of plan.steps) {
    const item=document.createElement('article');
    const heading=document.createElement('strong');
    heading.textContent=step.label;
    const meta=document.createElement('p');
    meta.className='muted';
    meta.textContent=agents.get(step.agentId)+' · '+step.key+
      ' · '+step.status.replaceAll('_',' ')+
      (step.dependencies.length ? ' · after '+step.dependencies.join(', ') : '');
    item.append(heading,meta);
    if (step.linkedTaskId) {
      const id=document.createElement('code');
      id.textContent='Task '+step.linkedTaskId;
      item.append(id);
    } else if (step.status === 'ready_for_operator_link' &&
               plan.status === 'operator_planning') {
      const wrapper=document.createElement('div');
      wrapper.className='tasklink';
      const input=document.createElement('input');
      input.placeholder='Existing EXODIA task UUID';
      input.setAttribute('aria-label','Task ID for '+step.label);
      input.maxLength=128;
      const button=document.createElement('button');
      button.type='button';
      button.textContent='Link task';
      button.addEventListener('click',async()=>{
        const taskId=input.value.trim();
        if(!/^[A-Za-z0-9-]{1,128}$/.test(taskId)){
          showNotice('Enter an existing task ID from the Command Center',true);
          return;
        }
        button.disabled=true;
        try {
          await request('/api/command/workflows/'+encodeURIComponent(plan.id)+'/bind',{
            method:'POST',
            headers:{'Content-Type':'application/json'},
            body:JSON.stringify({step_key:step.key,task_id:taskId,
                                 expected_revision:plan.revision})
          });
          showNotice('Task linked. Rechecked dependency evidence.');
          window.dispatchEvent(new Event('exodia:workflow-change'));
          await selectPlan(plan.id);
        } catch (_) {
          showNotice('Task link rejected: verify assignment, dependency and revision.',true);
          await selectPlan(plan.id);
        } finally {button.disabled=false;}
      });
      wrapper.append(input,button);
      item.append(wrapper);
    }
    slot.append(item);
  }
  byId('progressStatus').textContent=plan.completed+' / '+plan.stepCount+
    ' actual answered tasks · external execution disabled';
  byId('confirmReview').disabled=(
    plan.status!=='operator_planning' ||
    plan.completed!==plan.stepCount
  );
  byId('forkRecovery').disabled=!(
    plan.status==='reviewed_local_only' ||
    plan.steps.some(item=>item.status==='linked_task_failed')
  );
}

async function selectPlan(id) {
  const serial=++selectionRevision;
  try {
    const raw=await request('/api/command/workflows/'+encodeURIComponent(id));
    const plan=safeWorkflow(raw);
    if(serial!==selectionRevision)return;
    selected=plan;
    renderPlan(plan);
    const evidenceSlot=byId('workflowEvidenceStatus');
    if(evidenceSlot){
      evidenceSlot.textContent='Corroborating Inbox task events…';
      try {
        const rawEvidence=await request('/api/command/workflows/'+
          encodeURIComponent(plan.id)+'/evidence');
        const audit=safeWorkflowEvidence(rawEvidence);
        if(serial!==selectionRevision)return;
        if(audit.workflowId!==plan.id||audit.revision!==plan.revision)
          throw new Error('Stale workflow evidence');
        evidenceSlot.textContent=audit.confirmed+'/'+audit.answered+
          ' answered tasks have recorded transition evidence · '+
          audit.nextAction.replaceAll('_',' ')+
          ' · authenticated provider acceptance not established';
      }catch(_){
        if(serial!==selectionRevision)return;
        evidenceSlot.textContent='Task event evidence unavailable · no success claimed';
      }
    }
    await refreshPlans();
  } catch (_) {
    if(serial!==selectionRevision)return;
    showNotice('Unable to inspect the selected workflow',true);
  }
}

byId('addStage').addEventListener('click',addStage);
byId('refreshPlans').addEventListener('click',()=>{void refreshPlans();});
byId('planForm').addEventListener('submit',async event=>{
  event.preventDefault();
  const btn=byId('createPlan');
  btn.disabled=true;
  try {
    const body=compilePlan();
    const raw=await request('/api/command/workflows',{
      method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify(body)
    });
    const plan=safeWorkflow(raw);
    showNotice('Saved operator plan. No tasks were sent.');
    window.dispatchEvent(new Event('exodia:workflow-change'));
    byId('planForm').reset();
    stageEditors.replaceChildren();
    addStage();
    await selectPlan(plan.id);
  } catch (_) {
    showNotice('Plan not saved. Check labels, companion IDs and stage dependencies.',true);
  } finally {btn.disabled=false;}
});
byId('forkRecovery').addEventListener('click',async()=>{
  if(!selected ||
    !(selected.status==='reviewed_local_only' ||
      selected.steps.some(step=>step.status==='linked_task_failed')))return;
  if(!window.confirm('Create a NEW unlinked local recovery plan? All existing tasks, approvals and results remain unchanged. No providers are contacted.'))
    return;
  const source=selected.id;
  const revision=selected.revision;
  const control=byId('forkRecovery');
  control.disabled=true;
  try {
    const payload=await request('/api/command/workflows/'+encodeURIComponent(source)+'/fork',{
      method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({expected_revision:revision,confirmation:'CREATE LOCAL RECOVERY PLAN'})
    });
    const {fresh:fork}=safeRecoveryFork(payload,source,revision);
    showNotice('New recovery plan saved. Existing tasks and approvals preserved.');
    window.dispatchEvent(new Event('exodia:workflow-change'));
    await selectPlan(fork.id);
  }catch(_){
    showNotice('Recovery fork rejected; check failed/reviewed status and current revision.',true);
    await selectPlan(source);
  }finally{
    control.disabled=false;
  }
});
byId('confirmReview').addEventListener('click',async()=>{
  if(!selected || selected.completed!==selected.stepCount ||
     selected.status!=='operator_planning')return;
  if(!window.confirm('Confirm LOCAL review only? This will not publish or dispatch tasks.'))
    return;
  try {
    await request('/api/command/workflows/'+encodeURIComponent(selected.id)+'/review',{
      method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({
        expected_revision:selected.revision,
        confirmation:'CONFIRM LOCAL WORKFLOW REVIEW'
      })
    });
    showNotice('Local workflow review recorded. No external action authorized.');
    window.dispatchEvent(new Event('exodia:workflow-change'));
    await selectPlan(selected.id);
  } catch (_) {
    showNotice('Review rejected. Verify all tasks are actually answered.',true);
    await selectPlan(selected.id);
  }
});
addStage();
void refreshPlans();
