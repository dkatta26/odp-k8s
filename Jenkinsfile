def runtimestages = selectedStages("${params.STAGES}")
def runtimUser = "${params.USER}"

pipeline {
    agent any

    stages {
        stage('Selected_Components')
                {
                    steps
                            {
                                echo "${runtimestages}"
                                echo "${runtimUser}"
                            }
                }
        stage('Hello') {
            when {
                expression {
                    runtimestages.contains('Hello')
                }
            }
            steps {
                script{
                    echo 'mvn clean install'
                }

            }
        }
        stage('first_code') {
            when {
                expression {
                    runtimestages.contains('first_code')
                }
            }
            steps {
                script{
                    echo 'first code written'
                }

            }
        }
        stage('second_code') {

            when {
                expression {
                    runtimestages.contains('second_code')
                }
            }
            steps {
                script{
                    echo 'second code written'
                }

            }

        }
        stage('third_code') {

            when {
                expression {
                    runtimestages.contains('third_code')
                }
            }
            steps {
                script{
                    echo 'third code written'
                }

            }
        }
        stage('fourth_code') {

            when {
                expression {
                    runtimestages.contains('fourth_code')
                }
            }
            steps {
                script{
                    echo 'fourth code written'
                }

            }
        }
        stage('fifth_code') {

            when {
                expression {
                    runtimestages.contains('fifth_code')
                }
            }
            steps {
                script{
                    echo 'fifth code written'
                }

            }
        }
    }
}

def selectedStages(String STAGES) {
    return STAGES.split(',')
}

