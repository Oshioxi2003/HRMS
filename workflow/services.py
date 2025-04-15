from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone
from .models import WorkflowDefinition, WorkflowStep, WorkflowInstance, WorkflowStepInstance
from employee.models import Employee
from notifications.services import create_notification

User = get_user_model()

class WorkflowService:
    @staticmethod
    def start_workflow(entity, entity_type, initiator):
        """
        Start a workflow for a specific entity
        
        Args:
            entity: The model instance for which to start the workflow
            entity_type: String identifier for the entity type (e.g., 'leave_request')
            initiator: User who initiated the workflow
        
        Returns:
            WorkflowInstance or None if no workflow defined
        """
        # Find active workflow definition for this entity type
        workflow_def = WorkflowDefinition.objects.filter(
            entity_type=entity_type,
            is_active=True
        ).first()
        
        if not workflow_def:
            return None
        
        # Create workflow instance
        content_type = ContentType.objects.get_for_model(entity)
        workflow_instance = WorkflowInstance.objects.create(
            workflow=workflow_def,
            content_type=content_type,
            object_id=entity.pk,
            initiator=initiator,
            status='in_progress'
        )
        
        # Create step instances
        first_step = None
        for step in workflow_def.steps.all().order_by('order'):
            step_instance = WorkflowStepInstance.objects.create(
                workflow_instance=workflow_instance,
                workflow_step=step
            )
            
            if not first_step:
                first_step = step_instance
        
        if first_step:
            # Set current step and process it
            workflow_instance.current_step = first_step.workflow_step
            workflow_instance.save()
            
            # Process the first step
            WorkflowService.process_step(first_step)
        
        return workflow_instance
    
    @staticmethod
    def process_step(step_instance):
        """
        Process a workflow step instance
        
        Args:
            step_instance: WorkflowStepInstance to process
        """
        step = step_instance.workflow_step
        workflow_instance = step_instance.workflow_instance
        entity = workflow_instance.content_object
        
        # Mark step as in progress
        step_instance.status = 'in_progress'
        step_instance.started_date = timezone.now()
        
        # Handle different step types
        if step.step_type == 'approval':
            # Find approver based on approver_type
            approver = WorkflowService.get_approver(
                step.approver_type, 
                step.specific_approver, 
                entity,
                workflow_instance.initiator
            )
            
            if approver:
                step_instance.assigned_to = approver
                step_instance.save()
                
                # Send notification to approver
                create_notification(
                    user=approver,
                    notification_type='Workflow',
                    title=f'Approval Required: {step.step_name}',
                    message=f'Your approval is required for {workflow_instance.workflow.name}.',
                    link=f'/workflow/approve/{step_instance.step_instance_id}/'
                )
            else:
                # No approver found, skip this step
                step_instance.status = 'skipped'
                step_instance.completed_date = timezone.now()
                step_instance.comments = 'Skipped due to no approver found'
                step_instance.save()
                
                # Move to next step
                WorkflowService.move_to_next_step(workflow_instance)
                
        elif step.step_type == 'notification':
            # Process notification step
            # Implement notification logic here
            step_instance.status = 'completed'
            step_instance.completed_date = timezone.now()
            step_instance.save()
            
            # Move to next step
            WorkflowService.move_to_next_step(workflow_instance)
            
        elif step.step_type == 'auto_action':
            # Process automated action step
            # Implement automation logic here
            step_instance.status = 'completed'
            step_instance.completed_date = timezone.now()
            step_instance.save()
            
            # Move to next step
            WorkflowService.move_to_next_step(workflow_instance)
    
    @staticmethod
    def get_approver(approver_type, specific_approver, entity, initiator):
        """
        Get the appropriate approver based on the approver type
        
        Args:
            approver_type: Type of approver (e.g., 'manager', 'hr')
            specific_approver: Specific user (if approver_type is 'specific_user')
            entity: The entity being approved
            initiator: User who initiated the workflow
        
        Returns:
            User instance or None
        """
        if approver_type == 'specific_user' and specific_approver:
            return specific_approver
        
        if approver_type == 'manager':
            # Get employee's manager
            try:
                employee = Employee.objects.get(user=initiator)
                if employee.department:
                    manager = User.objects.filter(
                        employee__department=employee.department,
                        employee__position__position_name__icontains='Manager',
                        is_active=True
                    ).first()
                    return manager
            except Employee.DoesNotExist:
                pass
        
        elif approver_type == 'department_head':
            # Get department head
            try:
                employee = Employee.objects.get(user=initiator)
                if employee.department:
                    dept_head = User.objects.filter(
                        employee__department=employee.department,
                        employee__position__position_name__icontains='Head',
                        is_active=True
                    ).first()
                    
                    # If no explicit head, try finding manager
                    if not dept_head:
                        dept_head = User.objects.filter(
                            employee__department=employee.department,
                            employee__position__position_name__icontains='Manager',
                            is_active=True
                        ).first()
                    
                    return dept_head
            except Employee.DoesNotExist:
                pass
        
        elif approver_type == 'hr':
            # Get any HR personnel
            hr_user = User.objects.filter(role='HR', is_active=True).first()
            return hr_user
        
        elif approver_type == 'admin':
            # Get any admin
            admin_user = User.objects.filter(role='Admin', is_active=True).first()
            return admin_user
        
        return None
    
    @staticmethod
    def approve_step(step_instance, approver, comments=None):
        """
        Approve a workflow step
        
        Args:
            step_instance: WorkflowStepInstance to approve
            approver: User approving the step
            comments: Approval comments (optional)
        
        Returns:
            Boolean indicating success
        """
        if step_instance.status != 'in_progress':
            return False
        
        if step_instance.assigned_to != approver:
            return False
        
        # Mark step as approved
        step_instance.status = 'approved'
        step_instance.completed_date = timezone.now()
        step_instance.comments = comments
        step_instance.save()
        
        # Move to next step
        workflow_instance = step_instance.workflow_instance
        WorkflowService.move_to_next_step(workflow_instance)
        
        return True
    
    @staticmethod
    def reject_step(step_instance, approver, comments=None):
        """
        Reject a workflow step
        
        Args:
            step_instance: WorkflowStepInstance to reject
            approver: User rejecting the step
            comments: Rejection comments (optional)
        
        Returns:
            Boolean indicating success
        """
        if step_instance.status != 'in_progress':
            return False
        
        if step_instance.assigned_to != approver:
            return False
        
        # Mark step as rejected
        step_instance.status = 'rejected'
        step_instance.completed_date = timezone.now()
        step_instance.comments = comments
        step_instance.save()
        
        # Mark workflow as cancelled
        workflow_instance = step_instance.workflow_instance
        workflow_instance.status = 'cancelled'
        workflow_instance.completed_date = timezone.now()
        workflow_instance.save()
        
        # Notify initiator
        create_notification(
            user=workflow_instance.initiator,
            notification_type='Workflow',
            title=f'Workflow Rejected: {workflow_instance.workflow.name}',
            message=f'Your {workflow_instance.workflow.name} was rejected at step "{step_instance.workflow_step.step_name}". Comments: {comments or "None"}',
            link=f'/workflow/view/{workflow_instance.instance_id}/'
        )
        
        return True
    
    @staticmethod
    def move_to_next_step(workflow_instance):
        """
        Move workflow to the next step
        
        Args:
            workflow_instance: WorkflowInstance to progress
        
        Returns:
            Boolean indicating if there are more steps
        """
        current_step = workflow_instance.current_step
        
        if not current_step:
            # Workflow is complete
            workflow_instance.status = 'completed'
            workflow_instance.completed_date = timezone.now()
            workflow_instance.save()
            return False
        
        # Find next step
        next_step = WorkflowStep.objects.filter(
            workflow=workflow_instance.workflow,
            order__gt=current_step.order
        ).order_by('order').first()
        
        if not next_step:
            # No more steps, workflow is complete
            workflow_instance.status = 'completed'
            workflow_instance.current_step = None
            workflow_instance.completed_date = timezone.now()
            workflow_instance.save()
            
            # Notify initiator
            create_notification(
                user=workflow_instance.initiator,
                notification_type='Workflow',
                title=f'Workflow Completed: {workflow_instance.workflow.name}',
                message=f'Your {workflow_instance.workflow.name} has been fully approved.',
                link=f'/workflow/view/{workflow_instance.instance_id}/'
            )
            
            return False
        
        # Set current step to next step
        workflow_instance.current_step = next_step
        workflow_instance.save()
        
        # Get or create step instance
        step_instance, created = WorkflowStepInstance.objects.get_or_create(
            workflow_instance=workflow_instance,
            workflow_step=next_step,
            defaults={'status': 'pending'}
        )
        
        # Process the next step
        WorkflowService.process_step(step_instance)
        
        return True