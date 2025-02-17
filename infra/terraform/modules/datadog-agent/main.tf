# IAM Role Policy for Datadog agent
resource "aws_iam_role_policy" "ecs_execution_role_secret_policy" {
  name = "datadog-agent-secret-policy"
  role = aws_iam_role.ecs_execution_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "secretsmanager:GetSecretValue"
        ]
        Resource = [var.datadog_api_key_secret_arn]
      }
    ]
  })
}

# ECS Task Definition for Datadog agent
resource "aws_ecs_task_definition" "datadog_agent" {
  family                = "datadog-agent"
  network_mode         = "bridge"  # Changed from awsvpc to bridge
  cpu                  = 512
  memory               = 1024
  execution_role_arn   = aws_iam_role.ecs_execution_role.arn
  task_role_arn        = aws_iam_role.ecs_task_role.arn

  container_definitions = jsonencode([
    {
      name  = "datadog-agent"
      image = "public.ecr.aws/datadog/agent:latest"
      
      environment = [
        {
          name  = "DD_SITE"
          value = "datadoghq.com"
        }
      ]

       secrets = [
        {
          name      = "DD_API_KEY"
          valueFrom = var.datadog_api_key_secret_arn
        }
      ]

      mountPoints = [
        {
          sourceVolume  = "docker_sock"
          containerPath = "/var/run/docker.sock"
          readOnly      = true
        },
        {
          sourceVolume  = "proc"
          containerPath = "/host/proc"
          readOnly      = true
        },
        {
          sourceVolume  = "cgroup"
          containerPath = "/host/sys/fs/cgroup"
          readOnly      = true
        }
      ]

      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = "/ecs/datadog-agent"
          "awslogs-region"        = var.aws_region
          "awslogs-stream-prefix" = "ecs"
        }
      }
    }
  ])

  volume {
    name      = "docker_sock"
    host_path = "/var/run/docker.sock"
  }

  volume {
    name      = "proc"
    host_path = "/proc"
  }

  volume {
    name      = "cgroup"
    host_path = "/sys/fs/cgroup"
  }
}

# ECS Service
resource "aws_ecs_service" "datadog_agent" {
  name            = "datadog-agent"
  cluster         = var.ecs_cluster_id
  task_definition = aws_ecs_task_definition.datadog_agent.arn
  desired_count   = var.instance_count
  launch_type     = "EC2"  # Changed from FARGATE to EC2

  # Remove network_configuration block as it's not needed for EC2 launch type
}

# Security Group for EC2 instances
resource "aws_security_group" "datadog_agent" {
  name        = "datadog-agent"
  description = "Security group for Datadog agent EC2 instances"
  vpc_id      = var.vpc_id

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

