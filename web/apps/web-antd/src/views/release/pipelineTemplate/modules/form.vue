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
  schema: useSchema(false),
  showDefaultActions: false,
});

function getDefaultEnv(): string {
  return `DOCKER_REGISTRY = 'harbor.ynbigdata.com'
GIT_REPO = '\${GIT_REPO}'
IMAGE_BASE = "\${DOCKER_REGISTRY}/\${params.PROJECT}-\${params.MODULE}/\${params.APP}"`;
}

function getDefaultContent(_language?: string): string {
  const defaultEnv = getDefaultEnv();
  return `pipeline {
    agent any

    environment {
${defaultEnv.split('\n').map(l => `        ${l}`).join('\n')}
    }

    parameters {
        string(name: 'PROJECT', defaultValue: '\${PROJECT_NAME}', description: '项目名称')
        string(name: 'MODULE', defaultValue: '\${MODULE_NAME}', description: '模块名称')
        string(name: 'APP', defaultValue: '\${APP_NAME}', description: '应用名称')
        string(name: 'BRANCH', defaultValue: '\${BUILD_BRANCH}', description: '代码分支')
        string(name: 'VERSION', defaultValue: '', description: '版本号（可选）')
        choice(
            name: 'ENVIRONMENT',
            choices: ['dev', 'test', 'uat', 'prod'],
            description: '发布环境（若选择，将覆盖分支自动判断）'
        )
    }

    stages {
        stage('Print Build Parameters') {
            steps {
                echo "PROJECT    : \${params.PROJECT}"
                echo "MODULE     : \${params.MODULE}"
                echo "APP        : \${params.APP}"
                echo "BRANCH     : \${params.BRANCH}"
                echo "VERSION    : \${params.VERSION ?: '自动生成'}"
                echo "ENVIRONMENT: \${params.ENVIRONMENT}"
            }
        }

        stage('Checkout') {
            steps {
                git branch: params.BRANCH,
                    url: GIT_REPO,
                    credentialsId: 'gitlab-http-credentials'
            }
        }

        stage('Determine Version and Tag') {
            steps {
                script {
                    if (!params.VERSION) {
                        if (params.BRANCH == 'main' || params.BRANCH.startsWith('release/')) {
                            def versionFile = readFile('VERSION').trim()
                            currentBuild.displayName = "\${versionFile}"
                            env.VERSION = versionFile
                        } else {
                            env.VERSION = "test-\${env.BUILD_ID}"
                        }
                    } else {
                        env.VERSION = params.VERSION
                    }

                    if (params.ENVIRONMENT) {
                        env.TAG_SUFFIX = params.ENVIRONMENT
                    } else {
                        if (params.BRANCH == 'develop' || params.BRANCH.startsWith('feature/')) {
                            env.TAG_SUFFIX = 'test'
                        } else if (params.BRANCH == 'main' || params.BRANCH.startsWith('release/')) {
                            env.TAG_SUFFIX = 'uat'
                        } else if (params.BRANCH.startsWith('hotfix/')) {
                            env.TAG_SUFFIX = 'uat'
                        } else {
                            env.TAG_SUFFIX = 'test'
                        }
                    }

                    env.FULL_TAG = "\${env.VERSION}-\${env.TAG_SUFFIX}"
                    env.IMAGE = "\${IMAGE_BASE}:\${env.FULL_TAG}"

                    echo "构建标签: \${env.FULL_TAG}"
                    echo "镜像全名: \${env.IMAGE}"
                }
            }
        }

        stage('Build') {
            steps {
                script {
                    if ('\${CODE_SUBPATH}') {
                        dir('\${CODE_SUBPATH}') {
                            sh '\${BUILD_COMMAND}'
                        }
                    } else {
                        sh '\${BUILD_COMMAND}'
                    }
                }
            }
        }

        stage('Build Image') {
            steps {
                script {
                    def imageTag = "\${APP_CODE}:\${BUILD_NUMBER}"
                    if ('\${CODE_SUBPATH}') {
                        dir('\${CODE_SUBPATH}') {
                            sh "docker build -f \${DOCKERFILE_PATH} -t \${imageTag} --build-arg MODULE=\${params.MODULE} ."
                        }
                    } else {
                        sh "docker build -f \${DOCKERFILE_PATH} -t \${imageTag} --build-arg MODULE=\${params.MODULE} ."
                    }
                }
            }
        }

        stage('Push to Harbor') {
            steps {
                withCredentials([usernamePassword(
                    credentialsId: 'harbor-credentials',
                    passwordVariable: 'HARBOR_PASS',
                    usernameVariable: 'HARBOR_USER'
                )]) {
                    sh """
                        docker login \${DOCKER_REGISTRY} -u \${HARBOR_USER} -p \${HARBOR_PASS}
                        docker push \${IMAGE}
                        docker logout \${DOCKER_REGISTRY}
                    """
                }
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
      // 切换前先彻底清理表单状态（值、校验、dirty），
      // 避免编辑/创建来回切换时上一轮的字段值与校验状态残留
      formApi.resetForm();
      const data = modalApi.getData<PipelineTemplateApi.Template>();
      if (data?.id) {
        // 编辑模式
        formData.value = data;
        await loadData(data.id);

        formApi.setSchema(useSchema(true));
        formApi.updateSchema([
          { fieldName: 'code', componentProps: { disabled: true } },
        ]);
      } else {
        // 创建模式
        formData.value = undefined;

        formApi.setSchema(useSchema(false));
        formApi.updateSchema([
          { fieldName: 'code', componentProps: { disabled: false } },
        ]);

        formApi.setValues({
          name: '',
          code: '',
          language: 'java',
          language_version: '',
          framework: '',
          description: '',
          is_official: false,
          status: 1,
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
  const payload = {
    name: values.name,
    code: values.code,
    language: values.language,
    language_version: values.language_version,
    framework: values.framework,
    description: values.description,
    is_official: values.is_official,
    status: values.status,
  };
  if (isEdit.value) {
    modalApi.lock();
    try {
      // 模板主界面只维护元信息，Jenkinsfile 内容交由版本管理维护
      await updateTemplate(formData.value!.id!, payload);
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
      const template = await createTemplate(payload);
      message.success('模板创建成功');
      // 自动生成默认第一版本，便于在版本管理中查看/编辑
      const fullContent = getDefaultContent(values.language);
      await createTemplateVersion(template.id, {
        template: template.id,
        version: '1.0.0',
        content: fullContent,
        change_log: '初始版本（默认模板）',
        is_latest: true,
      });
      message.success('默认版本创建成功');
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
