import React, { useState } from 'react';
import { useTranslation } from 'react-i18next';
import MediaGenerationInterface from '../components/MediaGenerationInterface';
import { Model, ChatOutput } from '../@types/conversation';
import ChatMessage from '../components/ChatMessage';
import { DisplayMessageContent } from '../@types/conversation';

const MediaGenerationPage: React.FC = () => {
  const { t } = useTranslation();
  const [currentModel, setCurrentModel] = useState<Model>('amazon-nova-canvas');
  const [generatedResults, setGeneratedResults] = useState<ChatOutput[]>([]);

  const handleGenerationComplete = (result: ChatOutput) => {
    setGeneratedResults(prev => [...prev, result]);
  };

  const convertToDisplayMessage = (result: ChatOutput): DisplayMessageContent => {
    return {
      id: result.message.model + '-' + Date.now(),
      role: result.message.role,
      content: result.message.content,
      model: result.message.model,
      feedback: result.message.feedback,
      usedChunks: result.message.usedChunks,
      thinkingLog: result.message.thinkingLog,
      parent: null,
      children: [],
      sibling: [],
    };
  };

  return (
    <div className="flex flex-col h-screen bg-white dark:bg-gray-900">
      {/* Header */}
      <div className="border-b border-gray-200 dark:border-gray-700 p-4">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
          {t('mediaGeneration.pageTitle')}
        </h1>
        <p className="text-gray-600 dark:text-gray-400 mt-1">
          {t('mediaGeneration.pageDescription')}
        </p>
      </div>

      <div className="flex-1 flex overflow-hidden">
        {/* Generation Interface */}
        <div className="w-1/3 border-r border-gray-200 dark:border-gray-700 p-4 overflow-y-auto">
          <MediaGenerationInterface
            currentModel={currentModel}
            onModelChange={setCurrentModel}
            onGenerationComplete={handleGenerationComplete}
          />
        </div>

        {/* Results Display */}
        <div className="flex-1 p-4 overflow-y-auto">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
            {t('mediaGeneration.results')}
          </h2>
          
          {generatedResults.length === 0 ? (
            <div className="text-center text-gray-500 dark:text-gray-400 mt-8">
              <div className="text-6xl mb-4">🎨</div>
              <p>{t('mediaGeneration.noResults')}</p>
              <p className="text-sm mt-2">{t('mediaGeneration.getStarted')}</p>
            </div>
          ) : (
            <div className="space-y-6">
              {generatedResults.map((result, index) => (
                <div key={index} className="border border-gray-200 dark:border-gray-700 rounded-lg p-4">
                  <div className="text-sm text-gray-500 dark:text-gray-400 mb-2">
                    {new Date(result.createTime * 1000).toLocaleString()}
                  </div>
                  <ChatMessage
                    chatContent={convertToDisplayMessage(result)}
                  />
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default MediaGenerationPage;