from rest_framework import serializers
from django.contrib.auth import get_user_model
from employee.models import Employee, Department, Position
from attendance.models import Attendance
from leave.models import LeaveRequest
from tasks.models import Task
from notifications.models import Notification

User = get_user_model()

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'role', 'is_active']
        read_only_fields = ['id', 'username', 'role', 'is_active']

class DepartmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Department
        fields = ['department_id', 'department_name', 'department_code', 'description']

class PositionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Position
        fields = ['position_id', 'position_name', 'position_code', 'description']

class EmployeeSerializer(serializers.ModelSerializer):
    department = DepartmentSerializer(read_only=True)
    position = PositionSerializer(read_only=True)
    
    class Meta:
        model = Employee
        fields = [
            'employee_id', 'full_name', 'email', 'phone', 'date_of_birth', 'gender', 
            'hire_date', 'department', 'position', 'profile_image', 'status'
        ]

class AttendanceSerializer(serializers.ModelSerializer):
    employee = EmployeeSerializer(read_only=True)
    
    class Meta:
        model = Attendance
        fields = [
            'attendance_id', 'employee', 'work_date', 'time_in', 'time_out', 
            'actual_work_hours', 'overtime_hours', 'status'
        ]

class LeaveRequestSerializer(serializers.ModelSerializer):
    employee = EmployeeSerializer(read_only=True)
    
    class Meta:
        model = LeaveRequest
        fields = [
            'request_id', 'employee', 'leave_type', 'start_date', 'end_date', 
            'leave_days', 'reason', 'status', 'approval_date', 'approval_notes'
        ]
        read_only_fields = ['request_id', 'approval_date', 'approval_notes']

class TaskSerializer(serializers.ModelSerializer):
    assignee = EmployeeSerializer(read_only=True)
    
    class Meta:
        model = Task
        fields = [
            'task_id', 'title', 'description', 'assignee', 'priority', 'status',
            'start_date', 'due_date', 'completion_date', 'progress'
        ]
        read_only_fields = ['task_id', 'assignee']

class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = [
            'notification_id', 'notification_type', 'title', 'message',
            'link', 'is_read', 'created_date'
        ]
        read_only_fields = ['notification_id', 'created_date']