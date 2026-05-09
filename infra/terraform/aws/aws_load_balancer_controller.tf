data "aws_iam_openid_connect_provider" "eks" {
  url = data.aws_eks_cluster.this.identity[0].oidc[0].issuer
}

locals {
  oidc_provider_hostpath = replace(data.aws_iam_openid_connect_provider.eks.url, "https://", "")
}

resource "aws_iam_policy" "aws_load_balancer_controller" {
  name        = "${var.cluster_name}-aws-load-balancer-controller"
  description = "IAM policy for the AWS Load Balancer Controller on the x-clone EKS demo cluster."
  policy      = file("${path.module}/iam/aws-load-balancer-controller-policy.json")

  tags = {
    Project   = "x-clone-demo"
    ManagedBy = "terraform"
    Purpose   = "temporary-demo-ingress"
  }
}

resource "aws_iam_role" "aws_load_balancer_controller" {
  name = "${var.cluster_name}-aws-load-balancer-controller"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Federated = data.aws_iam_openid_connect_provider.eks.arn
        }
        Action = "sts:AssumeRoleWithWebIdentity"
        Condition = {
          StringEquals = {
            "${local.oidc_provider_hostpath}:aud" = "sts.amazonaws.com"
            "${local.oidc_provider_hostpath}:sub" = "system:serviceaccount:kube-system:aws-load-balancer-controller"
          }
        }
      }
    ]
  })

  tags = {
    Project   = "x-clone-demo"
    ManagedBy = "terraform"
    Purpose   = "temporary-demo-ingress"
  }
}

resource "aws_iam_role_policy_attachment" "aws_load_balancer_controller" {
  role       = aws_iam_role.aws_load_balancer_controller.name
  policy_arn = aws_iam_policy.aws_load_balancer_controller.arn
}

resource "helm_release" "aws_load_balancer_controller" {
  name       = "aws-load-balancer-controller"
  namespace  = "kube-system"
  repository = "https://aws.github.io/eks-charts"
  chart      = "aws-load-balancer-controller"
  version    = var.aws_load_balancer_controller_chart_version

  set {
    name  = "clusterName"
    value = var.cluster_name
  }

  set {
    name  = "region"
    value = var.aws_region
  }

  # Required when node IMDS is restricted: avoid controller startup
  # failures while discovering the cluster VPC from instance metadata.
  set {
    name  = "vpcId"
    value = data.aws_eks_cluster.this.vpc_config[0].vpc_id
  }

  set {
    name  = "serviceAccount.create"
    value = "true"
  }

  set {
    name  = "serviceAccount.name"
    value = "aws-load-balancer-controller"
  }

  set {
    name  = "serviceAccount.annotations.eks\\.amazonaws\\.com/role-arn"
    value = aws_iam_role.aws_load_balancer_controller.arn
  }

  set {
    name  = "ingressClassParams.create"
    value = "true"
  }

  set {
    name  = "ingressClassParams.name"
    value = "alb"
  }

  set {
    name  = "ingressClassParams.spec.group.name"
    value = "xclone-public"
  }

  set {
    name  = "ingressClassParams.spec.namespaceSelector.matchLabels.kubernetes\\.io/metadata\\.name"
    value = "xclone"
  }

  set {
    name  = "ingressClassParams.spec.scheme"
    value = "internet-facing"
  }

  set {
    name  = "ingressClassParams.spec.targetType"
    value = "ip"
  }

  set {
    name  = "ingressClassConfig.default"
    value = "false"
  }

  set {
    name  = "disableIngressGroupNameAnnotation"
    value = "true"
  }

  depends_on = [aws_iam_role_policy_attachment.aws_load_balancer_controller]
}
