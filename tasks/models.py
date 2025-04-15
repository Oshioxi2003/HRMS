from django.db import models
from django.contrib.auth import get_user_model
from employee.models import Employee, Department

User = get_user_model()

class TaskCategory(models.Model):
    category_id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=100)
    description = models.TextField(null=True, blank=True)
    color = models.CharField(max_length=7, default="#3498db")  # Hex color code
    is_active = models.BooleanField(default=True)
    created_date = models.DateTimeField(auto_now_add=True)
    updated_date = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.name
    
    class Meta:
        verbose_name_plural = "Task Categories"

class Task(models.Model):
    PRIORITY_CHOICES = (
        ('Low', 'Low'),
        ('Medium', 'Medium'),
        ('High', 'High'),
        ('Urgent', 'Urgent'),
    )
    
    STATUS_CHOICES = (
        ('Not Started', 'Not Started'),
        ('In Progress', 'In Progress'),
        ('On Hold', 'On Hold'),
        ('Completed', 'Completed'),
        ('Cancelled', 'Cancelled'),
    )
    
    task_id = models.AutoField(primary_key=True)
    title = models.CharField(max_length=200)
    description = models.TextField(null=True, blank=True)
    category = models.ForeignKey(TaskCategory, on_delete=models.SET_NULL, null=True, blank=True)
    assignee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='assigned_tasks')
    assigned_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_tasks')
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='Medium')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Not Started')
    start_date = models.DateField()
    due_date = models.DateField()
    completion_date = models.DateField(null=True, blank=True)
    progress = models.IntegerField(default=0)  # 0-100%
    is_recurring = models.BooleanField(default=False)
    recurrence_pattern = models.CharField(max_length=50, null=True, blank=True)  # e.g., "daily", "weekly", "monthly"
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True)
    attachments = models.FileField(upload_to='task_attachments/', null=True, blank=True)
    created_date = models.DateTimeField(auto_now_add=True)
    updated_date = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.title
    
    def is_overdue(self):
        from datetime import date
        return self.due_date < date.today() and self.status not in ['Completed', 'Cancelled']

class TaskComment(models.Model):
    comment_id = models.AutoField(primary_key=True)
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='comments')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    comment = models.TextField()
    attachment = models.FileField(upload_to='task_comment_attachments/', null=True, blank=True)
    created_date = models.DateTimeField(auto_now_add=True)
    updated_date = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Comment on {self.task.title} by {self.user.username}"
    
    class Meta:
        ordering = ['-created_date']

class TaskDependency(models.Model):
    dependency_id = models.AutoField(primary_key=True)
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='dependencies')
    dependent_on = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='dependents')
    created_date = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.task.title} depends on {self.dependent_on.title}"
    
    class Meta:
        unique_together = ('task', 'dependent_on')
        verbose_name_plural = "Task Dependencies"
