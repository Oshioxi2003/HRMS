from rest_framework import viewsets, permissions, status, filters
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from .serializers import (
    UserSerializer, EmployeeSerializer, DepartmentSerializer, PositionSerializer,
    AttendanceSerializer, LeaveRequestSerializer, TaskSerializer, NotificationSerializer
)
from .permissions import IsOwnerOrHR, IsManager, IsEmployeeOwner
from employee.models import *
from attendance.models import *
from leave.models import *
from tasks.models import *
from notifications.models import Notification
from datetime import date, datetime, timedelta
from accounts.models import *

from rest_framework import serializers




class UserViewSet(viewsets.ReadOnlyModelViewSet):
    """API endpoint that allows users to be viewed."""
    permission_classes = [IsAuthenticated]
    serializer_class = UserSerializer
    
    def get_queryset(self):
        user = self.request.user
        if user.role in ['HR', 'Admin']:
            return User.objects.all()
        elif user.role == 'Manager' and user.employee and user.employee.department:
            # Managers can see users in their department
            return User.objects.filter(employee__department=user.employee.department)
        else:
            return User.objects.filter(id=user.id)
    
    @action(detail=False, methods=['get'])
    def me(self, request):
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)

class EmployeeViewSet(viewsets.ReadOnlyModelViewSet):
    """API endpoint that allows employees to be viewed."""
    permission_classes = [IsAuthenticated]
    serializer_class = EmployeeSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ['full_name', 'email', 'phone']
    
    def get_queryset(self):
        user = self.request.user
        if user.role in ['HR', 'Admin']:
            return Employee.objects.all()
        elif user.role == 'Manager' and user.employee and user.employee.department:
            # Managers can see employees in their department
            return Employee.objects.filter(department=user.employee.department)
        elif user.employee:
            # Regular employees can only see themselves
            return Employee.objects.filter(employee_id=user.employee.employee_id)
        else:
            return Employee.objects.none()
    
    @action(detail=False, methods=['get'])
    def me(self, request):
        if request.user.employee:
            serializer = self.get_serializer(request.user.employee)
            return Response(serializer.data)
        return Response(
            {"detail": "Employee profile not found."},
            status=status.HTTP_404_NOT_FOUND
        )

class DepartmentViewSet(viewsets.ReadOnlyModelViewSet):
    """API endpoint that allows departments to be viewed."""
    permission_classes = [IsAuthenticated]
    queryset = Department.objects.filter(status=1)
    serializer_class = DepartmentSerializer

class PositionViewSet(viewsets.ReadOnlyModelViewSet):
    """API endpoint that allows positions to be viewed."""
    permission_classes = [IsAuthenticated]
    queryset = Position.objects.filter(status=1)
    serializer_class = PositionSerializer

class AttendanceViewSet(viewsets.ModelViewSet):
    """API endpoint that allows attendance records to be viewed or edited."""
    permission_classes = [IsAuthenticated, IsOwnerOrHR]
    serializer_class = AttendanceSerializer
    
    def get_queryset(self):
        user = self.request.user
        if user.role in ['HR', 'Admin']:
            return Attendance.objects.all()
        elif user.role == 'Manager' and user.employee and user.employee.department:
            # Managers can see attendance for their department
            return Attendance.objects.filter(employee__department=user.employee.department)
        elif user.employee:
            # Regular employees can only see their own attendance
            return Attendance.objects.filter(employee=user.employee)
        else:
            return Attendance.objects.none()
    
    @action(detail=False, methods=['post'])
    def check_in(self, request):
        if not request.user.employee:
            return Response(
                {"detail": "Employee profile not found."},
                status=status.HTTP_404_NOT_FOUND
            )
        
        today = date.today()
        now = datetime.now().time()
        
        try:
            # Check if there's already a record for today
            attendance = Attendance.objects.get(employee=request.user.employee, work_date=today)
            
            if attendance.time_in:
                return Response(
                    {"detail": "You have already checked in today."},
                    status=status.HTTP_400_BAD_REQUEST
                )
            else:
                attendance.time_in = now
                attendance.status = 'Present'
                attendance.save()
        except Attendance.DoesNotExist:
            # Create a new attendance record
            attendance = Attendance.objects.create(
                employee=request.user.employee,
                work_date=today,
                time_in=now,
                status='Present'
            )
        
        serializer = self.get_serializer(attendance)
        return Response(serializer.data)
    
    @action(detail=False, methods=['post'])
    def check_out(self, request):
        if not request.user.employee:
            return Response(
                {"detail": "Employee profile not found."},
                status=status.HTTP_404_NOT_FOUND
            )
        
        today = date.today()
        now = datetime.now().time()
        
        try:
            # Get today's attendance record
            attendance = Attendance.objects.get(employee=request.user.employee, work_date=today)
            
            if not attendance.time_in:
                return Response(
                    {"detail": "You need to check in first."},
                    status=status.HTTP_400_BAD_REQUEST
                )
            elif attendance.time_out:
                return Response(
                    {"detail": "You have already checked out today."},
                    status=status.HTTP_400_BAD_REQUEST
                )
            else:
                attendance.time_out = now
                
                # Calculate actual work hours
                time_in_dt = datetime.combine(today, attendance.time_in)
                time_out_dt = datetime.combine(today, now)
                
                if time_out_dt < time_in_dt:  # If checkout is on the next day
                    time_out_dt = datetime.combine(today + timedelta(days=1), now)
                
                diff_seconds = (time_out_dt - time_in_dt).total_seconds()
                diff_hours = diff_seconds / 3600
                
                attendance.actual_work_hours = round(diff_hours, 2)
                attendance.save()
                
                serializer = self.get_serializer(attendance)
                return Response(serializer.data)
        except Attendance.DoesNotExist:
            return Response(
                {"detail": "You need to check in first."},
                status=status.HTTP_400_BAD_REQUEST
            )

class LeaveRequestViewSet(viewsets.ModelViewSet):
    """API endpoint that allows leave requests to be viewed or edited."""
    permission_classes = [IsAuthenticated, IsEmployeeOwner]
    serializer_class = LeaveRequestSerializer
    
    def get_queryset(self):
        user = self.request.user
        if user.role in ['HR', 'Admin']:
            return LeaveRequest.objects.all()
        elif user.role == 'Manager' and user.employee and user.employee.department:
            # Managers can see leave requests for their department
            return LeaveRequest.objects.filter(employee__department=user.employee.department)
        elif user.employee:
            # Regular employees can only see their own leave requests
            return LeaveRequest.objects.filter(employee=user.employee)
        else:
            return LeaveRequest.objects.none()
    
    def perform_create(self, serializer):
        # Set employee automatically
        if not self.request.user.employee:
            raise serializers.ValidationError("Employee profile not found.")
        
        serializer.save(employee=self.request.user.employee)
    
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated, IsManager])
    def approve(self, request, pk=None):
        leave_request = self.get_object()
        
        # Check if request is pending
        if leave_request.status != 'Pending':
            return Response(
                {"detail": "This request is not pending approval."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if manager is in same department
        user = request.user
        if user.role not in ['HR', 'Admin'] and (
            not user.employee or 
            not leave_request.employee.department or 
            user.employee.department != leave_request.employee.department
        ):
            return Response(
                {"detail": "You don't have permission to approve this request."},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Update leave request
        leave_request.status = 'Approved'
        leave_request.approved_by = user.employee
        leave_request.approval_date = date.today()
        leave_request.approval_notes = request.data.get('approval_notes', '')
        leave_request.save()
        
        serializer = self.get_serializer(leave_request)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated, IsManager])
    def reject(self, request, pk=None):
        leave_request = self.get_object()
        
        # Check if request is pending
        if leave_request.status != 'Pending':
            return Response(
                {"detail": "This request is not pending approval."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if manager is in same department
        user = request.user
        if user.role not in ['HR', 'Admin'] and (
            not user.employee or 
            not leave_request.employee.department or 
            user.employee.department != leave_request.employee.department
        ):
            return Response(
                {"detail": "You don't have permission to reject this request."},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Validate rejection reason
        rejection_reason = request.data.get('approval_notes', '')
        if not rejection_reason:
            return Response(
                {"detail": "Please provide a reason for rejection."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Update leave request
        leave_request.status = 'Rejected'
        leave_request.approved_by = user.employee
        leave_request.approval_date = date.today()
        leave_request.approval_notes = rejection_reason
        leave_request.save()
        
        serializer = self.get_serializer(leave_request)
        return Response(serializer.data)

class TaskViewSet(viewsets.ModelViewSet):
    """API endpoint that allows tasks to be viewed or edited."""
    permission_classes = [IsAuthenticated]
    serializer_class = TaskSerializer
    
    def get_queryset(self):
        user = self.request.user
        if user.role in ['HR', 'Admin']:
            return Task.objects.all()
        elif user.role == 'Manager' and user.employee and user.employee.department:
            # Managers can see tasks for their department
            return Task.objects.filter(department=user.employee.department)
        elif user.employee:
            # Regular employees can only see tasks assigned to them
            return Task.objects.filter(assignee=user.employee)
        else:
            return Task.objects.none()
    
    @action(detail=True, methods=['post'])
    def update_status(self, request, pk=None):
        task = self.get_object()
        
        # Check if user is the assignee
        if request.user.employee != task.assignee:
            return Response(
                {"detail": "Only the assignee can update task status."},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Update status and progress
        status_value = request.data.get('status')
        progress = request.data.get('progress')
        
        if status_value:
            task.status = status_value
        
        if progress is not None:
            try:
                progress_value = int(progress)
                if 0 <= progress_value <= 100:
                    task.progress = progress_value
                else:
                    return Response(
                        {"detail": "Progress must be between 0 and 100."},
                        status=status.HTTP_400_BAD_REQUEST
                    )
            except ValueError:
                return Response(
                    {"detail": "Progress must be a number."},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        # If marking as completed, set completion date
        if task.status == 'Completed' and not task.completion_date:
            task.completion_date = date.today()
            task.progress = 100
        
        task.save()
        
        serializer = self.get_serializer(task)
        return Response(serializer.data)

class NotificationViewSet(viewsets.ReadOnlyModelViewSet):
    """API endpoint that allows notifications to be viewed."""
    permission_classes = [IsAuthenticated]
    serializer_class = NotificationSerializer
    
    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user).order_by('-created_date')
    
    @action(detail=True, methods=['post'])
    def mark_read(self, request, pk=None):
        notification = self.get_object()
        notification.is_read = True
        notification.save()
        
        serializer = self.get_serializer(notification)
        return Response(serializer.data)
    
    @action(detail=False, methods=['post'])
    def mark_all_read(self, request):
        Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
        return Response({"status": "All notifications marked as read"})
    


    