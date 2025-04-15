from django.db import models
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from employee.models import Employee

User = get_user_model()

class WorkflowDefinition(models.Model):
    """Definition of an approval workflow"""
    ENTITY_CHOICES = (
        ('leave_request', 'Leave Request'),
        ('expense_claim', 'Expense Claim'),
        ('asset_request', 'Asset Request'),
        ('contract', 'Contract'),
        ('task', 'Task'),
    )
    
    workflow_id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=100)
    description = models.TextField(null=True, blank=True)
    entity_type = models.CharField(max_length=50, choices=ENTITY_CHOICES)
    is_active = models.BooleanField(default=True)
    created_date = models.DateTimeField(auto_now_add=True)
    updated_date = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.name} ({self.entity_type})"

class WorkflowStep(models.Model):
    """Step in a workflow definition"""
    STEP_TYPE_CHOICES = (
        ('approval', 'Approval'),
        ('notification', 'Notification'),
        ('auto_action', 'Automated Action'),
    )
    
    APPROVER_TYPE_CHOICES = (
        ('specific_user', 'Specific User'),
        ('manager', 'Line Manager'),
        ('department_head', 'Department Head'),
        ('hr', 'HR Personnel'),
        ('admin', 'Administrator'),
    )
    
    step_id = models.AutoField(primary_key=True)
    workflow = models.ForeignKey(WorkflowDefinition, on_delete=models.CASCADE, related_name='steps')
    step_name = models.CharField(max_length=100)
    description = models.TextField(null=True, blank=True)
    step_type = models.CharField(max_length=20, choices=STEP_TYPE_CHOICES)
    approver_type = models.CharField(max_length=20, choices=APPROVER_TYPE_CHOICES, null=True, blank=True)
    specific_approver = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    order = models.IntegerField(default=1)
    is_required = models.BooleanField(default=True)
    skip_condition = models.TextField(null=True, blank=True)  # JSON or text condition
    created_date = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['workflow', 'order']
    
    def __str__(self):
        return f"{self.workflow.name} - Step {self.order}: {self.step_name}"

class WorkflowInstance(models.Model):
    """Instance of a workflow for a specific entity"""
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    )
    
    instance_id = models.AutoField(primary_key=True)
    workflow = models.ForeignKey(WorkflowDefinition, on_delete=models.CASCADE)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    initiator = models.ForeignKey(User, on_delete=models.CASCADE, related_name='initiated_workflows')
    current_step = models.ForeignKey(WorkflowStep, on_delete=models.SET_NULL, null=True, blank=True)
    started_date = models.DateTimeField(auto_now_add=True)
    completed_date = models.DateTimeField(null=True, blank=True)
    
    def __str__(self):
        return f"Workflow {self.workflow.name} for {self.content_type.model} ID:{self.object_id}"

class WorkflowStepInstance(models.Model):
    """Instance of a workflow step"""
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('skipped', 'Skipped'),
        ('completed', 'Completed'),
    )
    
    step_instance_id = models.AutoField(primary_key=True)
    workflow_instance = models.ForeignKey(WorkflowInstance, on_delete=models.CASCADE, related_name='step_instances')
    workflow_step = models.ForeignKey(WorkflowStep, on_delete=models.CASCADE)
    assigned_to = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    comments = models.TextField(null=True, blank=True)
    started_date = models.DateTimeField(null=True, blank=True)
    completed_date = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['workflow_instance', 'workflow_step__order']
    
    def __str__(self):
        return f"Step {self.workflow_step.order} for {self.workflow_instance}"