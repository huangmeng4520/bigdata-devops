import { describe, it, expect } from 'vitest';
import { parseStages, extractStageScript, updateStageSteps, validateJenkinsfile } from './jenkinsfileParser';

const sampleJenkinsfile = `pipeline {
    agent {
        kubernetes {
            label 'maven-builder'
            defaultContainer 'maven'
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
                sh 'mvn clean package -DskipTests'
            }
        }
        stage('Test') {
            steps {
                sh 'mvn test'
            }
        }
    }
}`;

describe('jenkinsfileParser', () => {
  describe('parseStages', () => {
    it('should parse stages from Jenkinsfile', () => {
      const stages = parseStages(sampleJenkinsfile);
      expect(stages).toHaveLength(3);
      expect(stages[0].name).toBe('Checkout');
      expect(stages[1].name).toBe('Build');
      expect(stages[2].name).toBe('Test');
    });

    it('should return empty array for empty content', () => {
      const stages = parseStages('');
      expect(stages).toHaveLength(0);
    });
  });

  describe('extractStageScript', () => {
    it('should extract steps content from stage', () => {
      const stages = parseStages(sampleJenkinsfile);
      const buildStage = stages.find(s => s.name === 'Build');
      expect(buildStage).toBeDefined();
      
      const script = extractStageScript(buildStage!.content);
      expect(script).toContain("sh 'mvn clean package -DskipTests'");
    });
  });

  describe('updateStageSteps', () => {
    it('should update stage steps in Jenkinsfile', () => {
      const newScript = "sh 'echo Building...'\nsh 'mvn clean install'";
      const updated = updateStageSteps(sampleJenkinsfile, 'Build', newScript);
      
      expect(updated).toContain('echo Building...');
      expect(updated).toContain('mvn clean install');
      expect(updated).not.toContain('mvn clean package -DskipTests');
    });

    it('should throw error for non-existent stage', () => {
      expect(() => {
        updateStageSteps(sampleJenkinsfile, 'NonExistent', 'echo test');
      }).toThrow('Stage "NonExistent" not found');
    });
  });

  describe('validateJenkinsfile', () => {
    it('should validate correct Jenkinsfile', () => {
      const result = validateJenkinsfile(sampleJenkinsfile);
      expect(result.valid).toBe(true);
    });

    it('should reject empty content', () => {
      const result = validateJenkinsfile('');
      expect(result.valid).toBe(false);
      expect(result.error).toContain('不能为空');
    });

    it('should reject invalid format', () => {
      const result = validateJenkinsfile('invalid content');
      expect(result.valid).toBe(false);
    });
  });
});
