pipeline {
    agent any
    
    parameters {
        string(
            name: 'REPO_URL',
            defaultValue: 'https://github.com/your-org/odp-on-k8s.git',
            description: 'Git repository URL for the build orchestration repo'
        )
        string(
            name: 'REPO_BRANCH',
            defaultValue: 'main',
            description: 'Git branch to checkout'
        )
        string(
            name: 'COMPONENTS_TO_BUILD',
            defaultValue: '',
            description: 'Comma-separated list of components to build (leave empty for all)'
        )
        string(
            name: 'ODP_RELEASE',
            defaultValue: 'ODP-3.3.6.3-1',
            description: 'ODP release version (used to lookup config)'
        )
        string(
            name: 'BIGTOP_BRANCH',
            defaultValue: 'rel/ODP-3.3.6.3-1',
            description: 'ODP Bigtop branch to use for builds'
        )
        string(
            name: 'DOCKER_IMAGE',
            defaultValue: 'repo1.acceldata.dev:8086/odp-images/build-env/rockylinux8:6',
            description: 'Docker image to use for build environment'
        )
        string(
            name: 'KUBECONFIG_PATH',
            defaultValue: '/odp-hz.yaml',
            description: 'Path to kubeconfig file'
        )
        string(
            name: 'NAMESPACE',
            defaultValue: 'build-deploy',
            description: 'Kubernetes namespace for builds'
        )
    }
    
    environment {
        KUBECONFIG = "${params.KUBECONFIG_PATH}"
    }
    
    stages {
        stage('Checkout Repository') {
            steps {
                script {
                    echo "============================================"
                    echo "Checking out repository"
                    echo "============================================"
                    echo "Repository: ${params.REPO_URL}"
                    echo "Branch: ${params.REPO_BRANCH}"
                    echo "ODP Release: ${params.ODP_RELEASE}"
                    echo "Bigtop Branch: ${params.BIGTOP_BRANCH}"
                    echo "Docker Image: ${params.DOCKER_IMAGE}"
                    echo "Components: ${params.COMPONENTS_TO_BUILD ?: 'ALL'}"
                    echo "============================================"
                }
                
                checkout([
                    $class: 'GitSCM',
                    branches: [[name: "*/${params.REPO_BRANCH}"]],
                    userRemoteConfigs: [[url: "${params.REPO_URL}"]]
                ])
                
                script {
                    echo "Repository checked out successfully"
                }
            }
        }
        
        stage('Validate Environment') {
            steps {
                script {
                    echo "============================================"
                    echo "Validating environment"
                    echo "============================================"
                }
                
                sh '''
                    echo "Checking Python version..."
                    python3 --version || {
                        echo "ERROR: Python3 is required"
                        exit 1
                    }
                    
                    echo "Checking kubectl access..."
                    kubectl version --client || {
                        echo "ERROR: kubectl is required"
                        exit 1
                    }
                    
                    echo "Installing Python dependencies..."
                    pip3 install -r requirements.txt --user || {
                        echo "ERROR: Failed to install Python dependencies"
                        exit 1
                    }
                    
                    echo "Environment validation completed"
                    echo "Note: Namespace and secret validation will happen in the Python script"
                '''
            }
        }
        
        stage('Run Build Orchestration') {
            steps {
                script {
                    echo "============================================"
                    echo "Starting build orchestration"
                    echo "============================================"
                }
                
                sh """
                    python3 src/main.py \
                        --release ${params.ODP_RELEASE} \
                        --components '${params.COMPONENTS_TO_BUILD}' \
                        --bigtop-branch ${params.BIGTOP_BRANCH} \
                        --docker-image ${params.DOCKER_IMAGE} \
                        --kubeconfig ${params.KUBECONFIG_PATH}
                """
            }
        }
    }
    
    post {
        always {
            script {
                echo "============================================"
                echo "Build Pipeline Completed"
                echo "============================================"
            }
        }
        success {
            script {
                echo "✓ All builds completed successfully!"
            }
        }
        failure {
            script {
                echo "✗ Build pipeline failed. Check logs above for details."
            }
        }
    }
}

