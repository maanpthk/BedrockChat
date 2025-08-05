import React, { useState } from 'react';
import { useTranslation } from 'react-i18next';
import Button from './Button';
import InputText from './InputText';
import Textarea from './Textarea';
import Slider from './Slider';
import { VideoGenerationRequestContent } from '../@types/conversation';

type Props = {
  onGenerate: (request: VideoGenerationRequestContent) => void;
  isGenerating: boolean;
};

const VideoGenerationForm: React.FC<Props> = ({ onGenerate, isGenerating }) => {
  const { t } = useTranslation();
  const [prompt, setPrompt] = useState('');
  const [negativePrompt, setNegativePrompt] = useState('');
  const [durationSeconds, setDurationSeconds] = useState(6);
  const [fps, setFps] = useState(24);
  const [seed, setSeed] = useState<number | undefined>(undefined);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!prompt.trim()) return;

    onGenerate({
      contentType: 'video_generation_request',
      prompt: prompt.trim(),
      negativePrompt: negativePrompt.trim() || undefined,
      durationSeconds,
      fps,
      seed,
    });
  };

  const fpsOptions = [12, 24, 30];

  return (
    <div className="space-y-4 p-4 border rounded-lg bg-gray-50 dark:bg-gray-800">
      <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
        {t('videoGeneration.title')}
      </h3>
      
      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
            {t('videoGeneration.prompt')} *
          </label>
          <Textarea
            value={prompt}
            onChange={setPrompt}
            placeholder={t('videoGeneration.promptPlaceholder')}
            rows={3}
            disabled={isGenerating}
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
            {t('videoGeneration.negativePrompt')}
          </label>
          <Textarea
            value={negativePrompt}
            onChange={setNegativePrompt}
            placeholder={t('videoGeneration.negativePromptPlaceholder')}
            rows={2}
            disabled={isGenerating}
          />
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              {t('videoGeneration.duration')}: {durationSeconds}s
            </label>
            <Slider
              value={durationSeconds}
              onChange={setDurationSeconds}
              min={1}
              max={6}
              step={1}
              disabled={isGenerating}
            />
            <div className="text-xs text-gray-500 mt-1">
              {t('videoGeneration.durationHelp')}
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              {t('videoGeneration.fps')}
            </label>
            <select
              className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:border-gray-600 dark:text-white"
              value={fps}
              onChange={(e) => setFps(parseInt(e.target.value))}
              disabled={isGenerating}
            >
              {fpsOptions.map((fpsOption) => (
                <option key={fpsOption} value={fpsOption}>
                  {fpsOption} FPS
                </option>
              ))}
            </select>
          </div>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
            {t('videoGeneration.seed')} ({t('videoGeneration.optional')})
          </label>
          <InputText
            type="number"
            value={seed?.toString() || ''}
            onChange={(value) => setSeed(value ? parseInt(value) : undefined)}
            placeholder={t('videoGeneration.seedPlaceholder')}
            disabled={isGenerating}
          />
        </div>

        <Button
          type="submit"
          disabled={!prompt.trim() || isGenerating}
          loading={isGenerating}
          className="w-full"
        >
          {isGenerating ? t('videoGeneration.generating') : t('videoGeneration.generate')}
        </Button>
      </form>
    </div>
  );
};

export default VideoGenerationForm;