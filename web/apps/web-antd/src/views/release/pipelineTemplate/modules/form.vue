<script lang="ts" setup>
import type { PipelineTemplateApi } from '#/api/release';

import { computed, ref } from 'vue';

import { useVbenModal } from '@vben/common-ui';

import { message } from 'ant-design-vue';

import { useVbenForm } from '#/adapter/form';
import {
  createTemplate,
  createTemplateVersion,
  getTemplateDetail,
  updateTemplate,
} from '#/api/release';
import { useSchema } from '../data';

const emit = defineEmits(['success']);

const formData = ref<Partial<PipelineTemplateApi.Template>>();
const isEdit = computed(() => !!formData.value?.id);
const modalTitle = computed(() => (isEdit.value ? '编辑模板' : '创建模板'));

const [Form, formApi] = useVbenForm({
  layout: 'vertical',
  schema: useSchema(false), // 初始显示所有字段
  showDefaultActions: false,
  handleValuesChange(values, fieldsChanged) {
    // 只在创建模式下，当语言或类型变化时更新 Jenkinsfile 内容
    if (!isEdit.value && 
        (fieldsChanged.includes('template_type') || fieldsChanged.includes('language'))) {
      const newContent = getDefaultContent(values.template_type as string, values.language as string);
      formApi.setFieldValue('content', newContent);
    }
  },
});

function getDefaultContent(templateType?: string, language?: string) {
  const tmplType = templateType || 'ci';
  const lang = language || 'java';

  if (tmplType === 'ci') {
    if (lang === 'java') {
      return `pipeline {
    agent {
        kubernetes {
            label 'maven-builder'
            defaultContainer 'maven'
        }
    }
    environment {
        MAVEN_OPTS = '-Dmaven.repo.local=/root/.m2/repository'
    }
    stages {
        stage('Checkout') {
            steps {
                checkout scm
            }
        }
        stage('Build') {
            steps {
                sh 'mvn clean package -DskipTests'
            }
        }
        stage('Test') {
            steps {
                sh 'mvn test'
            }
        }
        stage('Build Image') {
            steps {
                script {
                    def imageTag = "app:\${BUILD_NUMBER}"
                    sh """
                        docker build -t \${imageTag} .
                        docker push \${imageTag}
                    """
                }
            }
        }
    }
}`;
    } else if (lang === 'nodejs') {
      return `pipeline {
    agent {
        kubernetes {
            label 'node-builder'
            defaultContainer 'node'
        }
    }
    stages {
        stage('Checkout') {
            steps {
                checkout scm
            }
        }
        stage('Install') {
            steps {
                sh 'npm install'
            }
        }
        stage('Build') {
            steps {
                sh 'npm run build'
            }
        }
        stage('Test') {
            steps {
                sh 'npm test'
            }
        }
        stage('Build Image') {
            steps {
                script {
                    def imageTag = "app:\${BUILD_NUMBER}"
                    sh """
                        docker build -t \${imageTag} .
                        docker push \${imageTag}
                    """
                }
            }
        }
    }
}`;
    } else if (lang === 'python') {
      return `pipeline {
    agent {
        kubernetes {
            label 'python-builder'
            defaultContainer 'python'
        }
    }
    stages {
        stage('Checkout') {
            steps {
                checkout scm
            }
        }
        stage('Install') {
            steps {
                sh 'pip install -r requirements.txt'
            }
        }
        stage('Test') {
            steps {
                sh 'pytest'
            }
        }
        stage('Build Image') {
            steps {
                script {
                    def imageTag = "app:\${BUILD_NUMBER}"
                    sh """
                        docker build -t \${imageTag} .
                        docker push \${imageTag}
                    """
                }
            }
        }
    }
}`;
    } else if (lang === 'go') {
      return `pipeline {
    agent {
        kubernetes {
            label 'go-builder'
            defaultContainer 'golang'
        }
    }
    stages {
        stage('Checkout') {
            steps {
                checkout scm
            }
        }
        stage('Build') {
            steps {
                sh 'go build -o app'
            }
        }
        stage('Test') {
            steps {
                sh 'go test ./...'
            }
        }
        stage('Build Image') {
            steps {
                script {
                    def imageTag = "app:\${BUILD_NUMBER}"
                    sh """
                        docker build -t \${imageTag} .
                        docker push \${imageTag}
                    """
                }
            }
        }
    }
}`;
    } else if (lang === 'dotnet') {
      return `pipeline {
    agent {
        kubernetes {
            label 'dotnet-builder'
            defaultContainer 'dotnet'
        }
    }
    stages {
        stage('Checkout') {
            steps {
                checkout scm
            }
        }
        stage('Build') {
            steps {
                sh 'dotnet build'
            }
        }
        stage('Test') {
            steps {
                sh 'dotnet test'
            }
        }
        stage('Build Image') {
            steps {
                script {
                    def imageTag = "app:\${BUILD_NUMBER}"
                    sh """
                        docker build -t \${imageTag} .
                        docker push \${imageTag}
                    """
                }
            }
        }
    }
}`;
    }
  }
  
  // CD 模版
  return `pipeline {
    agent {
        kubernetes {
            label 'deployer'
        }
    }
    parameters {
        choice(name: 'ENV', choices: ['dev', 'test', 'staging', 'production'], description: '部署环境')
        string(name: 'IMAGE_TAG', description: '镜像标签')
    }
    stages {
        stage('Deploy') {
            steps {
                sh '''
                    echo "Deploying to \${ENV} with image \${IMAGE_TAG}"
                    # kubectl apply -f k8s/\${ENV}/
                '''
            }
        }
        stage('Health Check') {
            steps {
                sh '''
                    echo "Checking health..."
                    # kubectl rollout status deployment/app -n \${ENV}
                '''
            }
        }
    }
}`;
}

const [Modal, modalApi] = useVbenModal({
  async onConfirm() {
    await handleSubmit();
  },
  async onOpenChange(isOpen) {
    if (isOpen) {
      const data = modalApi.getData<PipelineTemplateApi.Template>();
      if (data?.id) {
        // 编辑模式：只显示基本信息，重新设置 schema
        formData.value = data;
        await loadData(data.id);
        
        // 重新设置为编辑模式的 schema（不包含版本字段）
        formApi.setSchema(useSchema(true));
        
        // 编辑模式下禁用模板编码和模板类型（这些字段不可修改，版本管理在版本管理页面）
        formApi.updateSchema([
          {
            fieldName: 'code',
            componentProps: { disabled: true },
          },
          {
            fieldName: 'template_type',
            componentProps: { disabled: true },
          },
        ]);
      } else {
        // 创建模式：显示版本字段
        formData.value = undefined;
        
        // 重新设置为创建模式的 schema（包含版本字段）
        formApi.setSchema(useSchema(false));
        
        const defaultContent = getDefaultContent();
        // 创建模式下启用所有字段
        formApi.updateSchema([
          {
            fieldName: 'code',
            componentProps: { disabled: false },
          },
          {
            fieldName: 'template_type',
            componentProps: { disabled: false },
          },
        ]);
        formApi.setValues({
          name: '',
          code: '',
          template_type: 'ci',
          language: 'java',
          language_version: '',
          framework: '',
          description: '',
          is_official: false,
          status: 1,
          version: '1.0.0',
          content: defaultContent,
          change_log: '初始版本',
          is_latest: true,
        });
      }
    }
  },
});

async function loadData(id: number) {
  try {
    const result = await getTemplateDetail(id);
    formData.value = result;
    formApi.setValues(result);
  } catch {
    message.error('加载数据失败');
  }
}

async function handleSubmit() {
  const values = await formApi.getValues();
  if (isEdit.value) {
    modalApi.lock();
    try {
      await updateTemplate(formData.value!.id!, values);
      message.success('更新成功');
      modalApi.close();
      emit('success');
    } catch (error: any) {
      message.error(error?.message || '更新失败');
    } finally {
      modalApi.lock(false);
    }
  } else {
    modalApi.lock();
    try {
      const template = await createTemplate({
        name: values.name,
        code: values.code,
        template_type: values.template_type,
        language: values.language,
        language_version: values.language_version,
        framework: values.framework,
        description: values.description,
        is_official: values.is_official,
        status: values.status,
      });
      message.success('模板创建成功');

      if (values.version && values.content) {
        await createTemplateVersion(template.id, {
          template: template.id,
          version: values.version,
          content: values.content,
          change_log: values.change_log || '初始版本',
          is_latest: values.is_latest,
        });
        message.success('版本创建成功');
      }
      modalApi.close();
      emit('success');
    } catch (error: any) {
      message.error(error?.message || '操作失败');
    } finally {
      modalApi.lock(false);
    }
  }
}
</script>

<template>
  <Modal :title="modalTitle">
    <Form />
  </Modal>
</template>
