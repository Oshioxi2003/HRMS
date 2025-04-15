from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Count
from django.http import JsonResponse
from django.utils import timezone
import json
from django.contrib.auth import get_user_model
from .models import WorkflowDefinition, WorkflowStep, WorkflowInstance, WorkflowStepInstance
from .services import WorkflowService
from .forms import (WorkflowDefinitionForm, WorkflowStepForm, 
                   StepReorderForm, WorkflowStepActionForm)
from accounts.decorators import hr_required, admin_required

User = get_user_model()

@login_required
def my_approval_requests(request):
    """View approval requests assigned to the current user"""
    step_instances = WorkflowStepInstance.objects.filter(
        assigned_to=request.user,
        status='in_progress'
    ).select_related(
        'workflow_instance', 
        'workflow_step',
        'workflow_instance__workflow'
    ).order_by('workflow_instance__started_date')
    
    # Get counts by status
    pending_count = step_instances.count()
    completed_count = WorkflowStepInstance.objects.filter(
        assigned_to=request.user,
        status__in=['approved', 'rejected']
    ).count()
    
    return render(request, 'workflow/my_approval_requests.html', {
        'step_instances': step_instances,
        'pending_count': pending_count,
        'completed_count': completed_count
    })

@login_required
def my_workflows(request):
    """View workflows initiated by the current user"""
    # Default to showing active workflows
    status_filter = request.GET.get('status', 'active')
    
    if status_filter == 'active':
        workflows = WorkflowInstance.objects.filter(
            initiator=request.user,
            status__in=['pending', 'in_progress']
        )
    elif status_filter == 'completed':
        workflows = WorkflowInstance.objects.filter(
            initiator=request.user,
            status='completed'
        )
    elif status_filter == 'cancelled':
        workflows = WorkflowInstance.objects.filter(
            initiator=request.user,
            status='cancelled'
        )
    else:  # 'all'
        workflows = WorkflowInstance.objects.filter(
            initiator=request.user
        )
    
    # Get related data and order by most recent first
    workflows = workflows.select_related(
        'workflow', 'current_step'
    ).order_by('-started_date')
    
    # Get counts by status
    pending_count = WorkflowInstance.objects.filter(
        initiator=request.user,
        status__in=['pending', 'in_progress']
    ).count()
    
    completed_count = WorkflowInstance.objects.filter(
        initiator=request.user,
        status='completed'
    ).count()
    
    cancelled_count = WorkflowInstance.objects.filter(
        initiator=request.user,
        status='cancelled'
    ).count()
    
    return render(request, 'workflow/my_workflows.html', {
        'workflows': workflows,
        'status_filter': status_filter,
        'pending_count': pending_count,
        'completed_count': completed_count,
        'cancelled_count': cancelled_count
    })

@login_required
def workflow_detail(request, instance_id):
    """View workflow details"""
    workflow = get_object_or_404(WorkflowInstance, instance_id=instance_id)
    
    # Check if user has permission to view this workflow
    if request.user != workflow.initiator and not request.user.role in ['HR', 'Admin']:
        is_approver = WorkflowStepInstance.objects.filter(
            workflow_instance=workflow,
            assigned_to=request.user
        ).exists()
        
        if not is_approver:
            messages.error(request, "You don't have permission to view this workflow.")
            return redirect('dashboard')
    
    # Get step instances
    step_instances = WorkflowStepInstance.objects.filter(
        workflow_instance=workflow
    ).select_related('workflow_step', 'assigned_to').order_by('workflow_step__order')
    
    # Get entity details
    entity = workflow.content_object
    
    return render(request, 'workflow/workflow_detail.html', {
        'workflow': workflow,
        'step_instances': step_instances,
        'entity': entity
    })

@login_required
def approve_workflow_step(request, step_instance_id):
    """Approve or reject a workflow step"""
    step_instance = get_object_or_404(WorkflowStepInstance, step_instance_id=step_instance_id)
    
    # Check if user is the assigned approver
    if step_instance.assigned_to != request.user:
        messages.error(request, "You are not authorized to approve this step.")
        return redirect('my_approval_requests')
    
    # Check if step is in progress
    if step_instance.status != 'in_progress':
        messages.error(request, f"This step is already {step_instance.get_status_display()}.")
        return redirect('workflow_detail', instance_id=step_instance.workflow_instance.instance_id)
    
    if request.method == 'POST':
        form = WorkflowStepActionForm(request.POST)
        if form.is_valid():
            action = form.cleaned_data['action']
            comments = form.cleaned_data['comments']
            
            if action == 'approve':
                success = WorkflowService.approve_step(step_instance, request.user, comments)
                if success:
                    messages.success(request, "Step approved successfully.")
                else:
                    messages.error(request, "Failed to approve step.")
            elif action == 'reject':
                if not comments:
                    messages.error(request, "Please provide a reason for rejection.")
                    return render(request, 'workflow/approve_step.html', {
                        'form': form,
                        'step_instance': step_instance,
                        'workflow': step_instance.workflow_instance,
                        'entity': step_instance.workflow_instance.content_object
                    })
                
                success = WorkflowService.reject_step(step_instance, request.user, comments)
                if success:
                    messages.success(request, "Step rejected successfully.")
                else:
                    messages.error(request, "Failed to reject step.")
            
            return redirect('my_approval_requests')
    else:
        form = WorkflowStepActionForm()
    
    return render(request, 'workflow/approve_step.html', {
        'form': form,
        'step_instance': step_instance,
        'workflow': step_instance.workflow_instance,
        'entity': step_instance.workflow_instance.content_object
    })

@login_required
@hr_required
def workflow_definitions(request):
    """List workflow definitions"""
    definitions = WorkflowDefinition.objects.all().order_by('-is_active', 'name')
    
    # Count steps for each definition
    for definition in definitions:
        definition.step_count = WorkflowStep.objects.filter(workflow=definition).count()
        definition.instance_count = WorkflowInstance.objects.filter(workflow=definition).count()
    
    return render(request, 'workflow/workflow_definitions.html', {
        'definitions': definitions
    })

@login_required
@hr_required
def workflow_definition_create(request):
    """Create new workflow definition"""
    if request.method == 'POST':
        form = WorkflowDefinitionForm(request.POST)
        if form.is_valid():
            workflow = form.save()
            messages.success(request, f"Workflow '{workflow.name}' created successfully. Now add steps to the workflow.")
            return redirect('workflow_step_create', workflow_id=workflow.workflow_id)
    else:
        form = WorkflowDefinitionForm()
    
    return render(request, 'workflow/workflow_definition_form.html', {
        'form': form,
        'title': 'Create Workflow Definition',
        'is_edit': False
    })

@login_required
@hr_required
def workflow_definition_edit(request, workflow_id):
    """Edit workflow definition"""
    workflow = get_object_or_404(WorkflowDefinition, workflow_id=workflow_id)
    
    if request.method == 'POST':
        form = WorkflowDefinitionForm(request.POST, instance=workflow)
        if form.is_valid():
            workflow = form.save()
            messages.success(request, f"Workflow '{workflow.name}' updated successfully.")
            return redirect('workflow_definition_detail', workflow_id=workflow.workflow_id)
    else:
        form = WorkflowDefinitionForm(instance=workflow)
    
    return render(request, 'workflow/workflow_definition_form.html', {
        'form': form,
        'title': 'Edit Workflow Definition',
        'is_edit': True,
        'workflow': workflow
    })

@login_required
@hr_required
def workflow_definition_detail(request, workflow_id):
    """View workflow definition details"""
    definition = get_object_or_404(WorkflowDefinition, workflow_id=workflow_id)
    steps = WorkflowStep.objects.filter(workflow=definition).order_by('order')
    
    # Count active instances
    active_instances = WorkflowInstance.objects.filter(
        workflow=definition,
        status__in=['pending', 'in_progress']
    ).count()
    
    return render(request, 'workflow/workflow_definition_detail.html', {
        'definition': definition,
        'steps': steps,
        'active_instances': active_instances
    })

@login_required
@hr_required
def workflow_definition_delete(request, workflow_id):
    """Delete workflow definition"""
    workflow = get_object_or_404(WorkflowDefinition, workflow_id=workflow_id)
    
    # Check if there are active instances
    active_instances = WorkflowInstance.objects.filter(
        workflow=workflow,
        status__in=['pending', 'in_progress']
    ).exists()
    
    if request.method == 'POST':
        if active_instances and not request.POST.get('confirm_active'):
            messages.error(request, "There are active workflow instances. Please confirm deletion.")
            return render(request, 'workflow/workflow_definition_delete.html', {
                'workflow': workflow,
                'active_instances': active_instances
            })
        
        workflow_name = workflow.name
        workflow.delete()
        messages.success(request, f"Workflow '{workflow_name}' deleted successfully.")
        return redirect('workflow_definitions')
    
    return render(request, 'workflow/workflow_definition_delete.html', {
        'workflow': workflow,
        'active_instances': active_instances
    })

@login_required
@hr_required
def workflow_step_create(request, workflow_id):
    """Create new workflow step"""
    workflow = get_object_or_404(WorkflowDefinition, workflow_id=workflow_id)
    
    if request.method == 'POST':
        form = WorkflowStepForm(request.POST, workflow=workflow)
        if form.is_valid():
            step = form.save(commit=False)
            step.workflow = workflow
            step.save()
            
            messages.success(request, f"Step '{step.step_name}' added successfully.")
            
            # If add another
            if 'save_and_add' in request.POST:
                return redirect('workflow_step_create', workflow_id=workflow_id)
            
            return redirect('workflow_definition_detail', workflow_id=workflow_id)
    else:
        form = WorkflowStepForm(workflow=workflow)
    
    # Get existing steps for reference
    existing_steps = WorkflowStep.objects.filter(workflow=workflow).order_by('order')
    
    return render(request, 'workflow/workflow_step_form.html', {
        'form': form,
        'workflow': workflow,
        'existing_steps': existing_steps,
        'title': 'Add Workflow Step',
        'is_edit': False
    })

@login_required
@hr_required
def workflow_step_edit(request, step_id):
    """Edit workflow step"""
    step = get_object_or_404(WorkflowStep, step_id=step_id)
    workflow = step.workflow
    
    if request.method == 'POST':
        form = WorkflowStepForm(request.POST, instance=step, workflow=workflow)
        if form.is_valid():
            step = form.save()
            messages.success(request, f"Step '{step.step_name}' updated successfully.")
            return redirect('workflow_definition_detail', workflow_id=workflow.workflow_id)
    else:
        form = WorkflowStepForm(instance=step, workflow=workflow)
    
    # Get existing steps for reference
    existing_steps = WorkflowStep.objects.filter(workflow=workflow).order_by('order')
    
    return render(request, 'workflow/workflow_step_form.html', {
        'form': form,
        'workflow': workflow,
        'existing_steps': existing_steps,
        'title': 'Edit Workflow Step',
        'is_edit': True,
        'step': step
    })

@login_required
@hr_required
def workflow_step_delete(request, step_id):
    """Delete workflow step"""
    step = get_object_or_404(WorkflowStep, step_id=step_id)
    workflow = step.workflow
    
    if request.method == 'POST':
        step_name = step.step_name
        
        # Get all steps with higher order
        higher_steps = WorkflowStep.objects.filter(
            workflow=workflow,
            order__gt=step.order
        )
        
        # Decrement order of higher steps
        for higher_step in higher_steps:
            higher_step.order -= 1
            higher_step.save()
        
        step.delete()
        messages.success(request, f"Step '{step_name}' deleted successfully.")
        return redirect('workflow_definition_detail', workflow_id=workflow.workflow_id)
    
    return render(request, 'workflow/workflow_step_delete.html', {
        'step': step,
        'workflow': workflow
    })

@login_required
@hr_required
def workflow_step_reorder(request, workflow_id):
    """Reorder workflow steps"""
    workflow = get_object_or_404(WorkflowDefinition, workflow_id=workflow_id)
    
    if request.method == 'POST':
        form = StepReorderForm(request.POST)
        if form.is_valid():
            step_order = json.loads(form.cleaned_data['step_order'])
            
            for order_data in step_order:
                step_id = order_data['id']
                new_order = order_data['order']
                
                step = get_object_or_404(WorkflowStep, step_id=step_id, workflow=workflow)
                step.order = new_order
                step.save()
            
            messages.success(request, "Workflow steps reordered successfully.")
            return redirect('workflow_definition_detail', workflow_id=workflow_id)
    
    # Get steps for drag and drop interface
    steps = WorkflowStep.objects.filter(workflow=workflow).order_by('order')
    
    return render(request, 'workflow/workflow_step_reorder.html', {
        'workflow': workflow,
        'steps': steps
    })

@login_required
@hr_required
def workflow_report(request):
    """Generate workflow reports"""
    # Filter parameters
    workflow_filter = request.GET.get('workflow', '')
    status_filter = request.GET.get('status', '')
    from_date = request.GET.get('from_date', '')
    to_date = request.GET.get('to_date', '')
    
    # Base query
    workflows = WorkflowInstance.objects.all().select_related(
        'workflow', 'initiator', 'current_step'
    )
    
    # Apply filters
    if workflow_filter:
        workflows = workflows.filter(workflow_id=workflow_filter)
    
    if status_filter:
        workflows = workflows.filter(status=status_filter)
    
    if from_date:
        workflows = workflows.filter(started_date__gte=from_date)
    
    if to_date:
        workflows = workflows.filter(started_date__lte=to_date)
    
    # Order by most recent first
    workflows = workflows.order_by('-started_date')
    
    # Get workflow definitions for filter dropdown
    definitions = WorkflowDefinition.objects.all().order_by('name')
    
    # Get statistics
    total_workflows = workflows.count()
    completed_count = workflows.filter(status='completed').count()
    cancelled_count = workflows.filter(status='cancelled').count()
    in_progress_count = workflows.filter(status__in=['pending', 'in_progress']).count()
    
    completion_rate = (completed_count / total_workflows * 100) if total_workflows > 0 else 0
    
    # Get average completion time for completed workflows
    avg_completion_time = None
    completed_workflows = workflows.filter(
        status='completed',
        completed_date__isnull=False
    )
    
    if completed_workflows.exists():
        total_days = 0
        count = 0
        
        for wf in completed_workflows:
            if wf.completed_date and wf.started_date:
                days = (wf.completed_date - wf.started_date).days
                total_days += days
                count += 1
        
        if count > 0:
            avg_completion_time = total_days / count
    
    return render(request, 'workflow/workflow_report.html', {
        'workflows': workflows,
        'definitions': definitions,
        'workflow_filter': workflow_filter,
        'status_filter': status_filter,
        'from_date': from_date,
        'to_date': to_date,
        'total_workflows': total_workflows,
        'completed_count': completed_count,
        'cancelled_count': cancelled_count,
        'in_progress_count': in_progress_count,
        'completion_rate': completion_rate,
        'avg_completion_time': avg_completion_time
    })
