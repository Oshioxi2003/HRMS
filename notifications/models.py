from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

class Notification(models.Model):
    NOTIFICATION_TYPES = (
        ('System', 'System Notification'),
        ('Leave', 'Leave Request'),
        ('Attendance', 'Attendance Alert'),
        ('Performance', 'Performance Review'),
        ('Contract', 'Contract Update'),
        ('Training', 'Training Invitation'),
        ('Salary', 'Salary Information'),
        ('Birthday', 'Birthday Reminder'),
        ('Task', 'Task Assignment'),
        ('Document', 'Document Update'),
    )
    
    notification_id = models.AutoField(primary_key=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES)
    title = models.CharField(max_length=200)
    message = models.TextField()
    link = models.CharField(max_length=255, null=True, blank=True)
    is_read = models.BooleanField(default=False)
    created_date = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_date']
    
    def __str__(self):
        return f"{self.user.username} - {self.title}"