import React, { useState } from 'react';
import { useTranslation } from 'react-i18next';
import Button from './Button';
import InputText from './InputText';
import Textarea from './Textarea';
import Slider from './Slider';
import { ImageGenerationRequestContent } from '../@types/conversation';

type Props = {
  onGenerate: (request: ImageGenerationRequestContent) => void;
  isGenerating: boolean;
};

const ImageGenerationForm: React.FC<Props> = ({ onGenerate, isGenerating }) => {
  const { t } = useTranslation();
  const [prompt, setPrompt] = useState('');
  const [negativePrompt, setNegativePrompt] = useState('');
  const [width, setWidth] = useState(1024);
  const [height, setHeight] = useState(1024);
  const [cfgScale, setCfgScale] = useState(7.0);
  const [seed, setSeed] = useState<number | undefined>(undefined);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!prompt.trim()) return;

    onGenerate({
      contentType: 'image_generation_request',
      prompt: prompt.trim(),
      negativePrompt: negativePrompt.trim() || undefined,
      width,
      height,
      cfgScale,
      seed,
    });
  };

  const commonSizes = [
    { label: '1:1 (1024x1024)', width: 1024, height: 1024 },
    { label: '16:9 (1344x768)', width: 1344, height: 768 },
    { label: '9:16 (768x1344)', width: 768, height: 1344 },
    { label: '4:3 (1152x896)', width: 1152, height: 896 },
    { label: '3:4 (896x1152)', width: 896, height: 1152 },
  ];

  return (
    <div className="space-y-4 p-4 border rounded-lg bg-gray-50 dark:bg-gray-800">
      <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
        {t('imageGeneration.title')}
      </h3>
      
      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
            {t('imageGeneration.prompt')} *
          </label>
          <Textarea
            value={prompt}
            onChange={setPrompt}
            placeholder={t('imageGeneration.promptPlaceholder')}
            rows={3}
            disabled={isGenerating}
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
            {t('imageGeneration.negativePrompt')}
          </label>
          <Textarea
            value={negativePrompt}
            onChange={setNegativePrompt}
            placeholder={t('imageGeneration.negativePromptPlaceholder')}
            rows={2}
            disabled={isGenerating}
          />
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              {t('imageGeneration.size')}
            </label>
            <select
              className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:border-gray-600 dark:text-white"
              value={`${width}x${height}`}
              onChange={(e) => {
                const [w, h] = e.target.value.split('x').map(Number);
                setWidth(w);
                setHeight(h);
              }}
              disabled={isGenerating}
            >
              {commonSizes.map((size) => (
                <option key={size.label} value={`${size.width}x${size.height}`}>
                  {size.label}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              {t('imageGeneration.cfgScale')}: {cfgScale}
            </label>
            <Slider
              value={cfgScale}
              onChange={setCfgScale}
              min={1}
              max={20}
              step={0.5}
              disabled={isGenerating}
            />
            <div className="text-xs text-gray-500 mt-1">
              {t('imageGeneration.cfgScaleHelp')}
            </div>
          </div>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
            {t('imageGeneration.seed')} ({t('imageGeneration.optional')})
          </label>
          <InputText
            type="number"
            value={seed?.toString() || ''}
            onChange={(value) => setSeed(value ? parseInt(value) : undefined)}
            placeholder={t('imageGeneration.seedPlaceholder')}
            disabled={isGenerating}
          />
        </div>

        <Button
          type="submit"
          disabled={!prompt.trim() || isGenerating}
          loading={isGenerating}
          className="w-full"
        >
          {isGenerating ? t('imageGeneration.generating') : t('imageGeneration.generate')}
        </Button>
      </form>
    </div>
  );
};

export default ImageGenerationForm;