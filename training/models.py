# training/models.py (updated)
from django.db import models
from employee.models import Employee, Department

class TrainingCourse(models.Model):
    STATUS_CHOICES = (
        ('Preparing', 'Preparing'),
        ('In Progress', 'In Progress'),
        ('Completed', 'Completed'),
        ('Cancelled', 'Cancelled'),
    )
    
    course_id = models.AutoField(primary_key=True)
    course_name = models.CharField(max_length=200)
    description = models.TextField(null=True, blank=True)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    location = models.CharField(max_length=200, null=True, blank=True)
    cost = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    organizer = models.CharField(max_length=100, null=True, blank=True)
    supervisor = models.CharField(max_length=100, null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Preparing')
    # Additional fields
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True, 
                                  help_text="If set, this course is specific to this department")
    max_participants = models.PositiveIntegerField(null=True, blank=True,
                                                 help_text="Maximum number of participants allowed")
    prerequisites = models.TextField(null=True, blank=True, 
                                    help_text="Prerequisites for attending this course")
    materials = models.TextField(null=True, blank=True,
                               help_text="Course materials and resources")
    image = models.ImageField(upload_to='training_images/', null=True, blank=True)
    created_date = models.DateTimeField(auto_now_add=True)
    updated_date = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.course_name
    
    def get_registration_count(self):
        return self.trainingparticipation_set.count()
    
    def is_full(self):
        if not self.max_participants:
            return False
        return self.get_registration_count() >= self.max_participants
    
    def get_available_slots(self):
        if not self.max_participants:
            return None
        return max(0, self.max_participants - self.get_registration_count())

class TrainingParticipation(models.Model):
    STATUS_CHOICES = (
        ('Registered', 'Registered'),
        ('Participating', 'Participating'),
        ('Completed', 'Completed'),
        ('Cancelled', 'Cancelled'),
    )
    
    participation_id = models.AutoField(primary_key=True)
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE)
    course = models.ForeignKey(TrainingCourse, on_delete=models.CASCADE)
    registration_date = models.DateField()
    # Additional fields
    expected_completion_date = models.DateField(null=True, blank=True)
    actual_completion_date = models.DateField(null=True, blank=True)
    approval_status = models.CharField(max_length=20, default='Approved', choices=[
        ('Pending', 'Pending'),
        ('Approved', 'Approved'),
        ('Rejected', 'Rejected')
    ])
    notes = models.TextField(null=True, blank=True)
    score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    achievement = models.CharField(max_length=100, null=True, blank=True)
    feedback = models.TextField(null=True, blank=True)
    certificate = models.CharField(max_length=100, null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Registered')
    created_date = models.DateTimeField(auto_now_add=True)
    updated_date = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ('employee', 'course')
    
    def __str__(self):
        return f"{self.employee.full_name} - {self.course.course_name}"
