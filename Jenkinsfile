pipeline {
    agent { label 'dev-build-deploy-hz' }
    
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
            description: 'ODP release version'
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
        booleanParam(
            name: 'DRY_RUN',
            defaultValue: false,
            description: 'Show build plan without executing'
        )
        booleanParam(
            name: 'NON_INTERACTIVE',
            defaultValue: true,
            description: 'Non-interactive mode (skip failed builds automatically)'
        )
        booleanParam(
            name: 'VERBOSE',
            defaultValue: false,
            description: 'Enable verbose logging'
        )
    }
    
    environment {
        KUBECONFIG = "${params.KUBECONFIG_PATH}"
    }
    
    stages {
        stage('Checkout') {
            steps {
                script {
                    echo "============================================"
                    echo "ODP BUILD PIPELINE"
                    echo "============================================"
                    echo "Repository: ${params.REPO_URL}"
                    echo "Branch: ${params.REPO_BRANCH}"
                    echo "ODP Release: ${params.ODP_RELEASE}"
                    echo "Bigtop Branch: ${params.BIGTOP_BRANCH}"
                    echo "Docker Image: ${params.DOCKER_IMAGE}"
                    echo "Components: ${params.COMPONENTS_TO_BUILD ?: 'ALL'}"
                    echo "Dry Run: ${params.DRY_RUN}"
                    echo "Non-Interactive: ${params.NON_INTERACTIVE}"
                    echo "============================================"
                }
                
                checkout([
                    $class: 'GitSCM',
                    branches: [[name: "*/${params.REPO_BRANCH}"]],
                    userRemoteConfigs: [[url: "${params.REPO_URL}"]]
                ])
                
                script {
                    echo "✓ Repository checked out successfully"
                }
            }
        }
        
        stage('Setup Environment') {
            steps {
                script {
                    echo "============================================"
                    echo "Setting up environment"
                    echo "============================================"
                }
                
                sh '''
                    set -e
                    
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
                    
                    echo "Checking kubeconfig..."
                    if [ ! -f "${KUBECONFIG}" ]; then
                        echo "ERROR: Kubeconfig file not found: ${KUBECONFIG}"
                        exit 1
                    fi
                    echo "✓ Kubeconfig found: ${KUBECONFIG}"
                    
                    echo "Installing Python dependencies..."
                    if [ -f requirements.txt ]; then
                        pip3 install -r requirements.txt --user || {
                            echo "ERROR: Failed to install Python dependencies"
                            exit 1
                        }
                    else
                        echo "WARNING: requirements.txt not found, skipping..."
                    fi
                    
                    echo "✓ Environment setup completed"
                '''
            }
        }
        
        stage('Validate Configuration') {
            steps {
                script {
                    echo "============================================"
                    echo "Validating configuration"
                    echo "============================================"
                }
                
                sh '''
                    set -e
                    
                    echo "Checking config files..."
                    if [ ! -f config/releases.yaml ]; then
                        echo "ERROR: config/releases.yaml not found"
                        exit 1
                    fi
                    
                    if [ ! -f config/components.yaml ]; then
                        echo "ERROR: config/components.yaml not found"
                        exit 1
                    fi
                    
                    echo "✓ Configuration files found"
                '''
            }
        }
        
        stage('Run Build Pipeline') {
            steps {
                script {
                    echo "============================================"
                    echo "Starting build orchestration"
                    echo "============================================"
                }
                
                script {
                    def cmd = "python3 src/main.py " +
                              "--release ${params.ODP_RELEASE} " +
                              "--components '${params.COMPONENTS_TO_BUILD}' " +
                              "--bigtop-branch ${params.BIGTOP_BRANCH} " +
                              "--docker-image ${params.DOCKER_IMAGE} " +
                              "--kubeconfig ${params.KUBECONFIG_PATH}"
                    
                    if (params.DRY_RUN) {
                        cmd += " --dry-run"
                    }
                    
                    if (params.NON_INTERACTIVE) {
                        cmd += " --non-interactive"
                    }
                    
                    if (params.VERBOSE) {
                        cmd += " --verbose"
                    }
                    
                    echo "Executing: ${cmd}"
                    
                    sh cmd
                }
            }
        }
    }
    
    post {
        always {
            script {
                echo "============================================"
                echo "Build Pipeline Completed"
                echo "============================================"
                echo "Release: ${params.ODP_RELEASE}"
                echo "Bigtop Branch: ${params.BIGTOP_BRANCH}"
                echo "Components: ${params.COMPONENTS_TO_BUILD ?: 'ALL'}"
                echo "============================================"
            }
        }
        success {
            script {
                echo "✓ BUILD PIPELINE COMPLETED SUCCESSFULLY!"
            }
        }
        failure {
            script {
                echo "✗ BUILD PIPELINE FAILED!"
                echo "Check logs above for details."
            }
        }
        unstable {
            script {
                echo "⚠ BUILD PIPELINE UNSTABLE"
            }
        }
    }
}
