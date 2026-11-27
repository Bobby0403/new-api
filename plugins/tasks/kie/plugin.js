// Kie Market model inputs: https://docs.kie.ai/market/quickstart
// Native inputs keep vendor field names; only documented fields are forwarded.
const MODELS = {
  "gpt-image-2-5-flare-text-to-image": {
    type: "image",
    fields: ["prompt", "aspect_ratio", "resolution", "background"],
    required: ["prompt"],
    enums: {
      aspect_ratio: ["auto", "1:1", "3:2", "2:3", "4:3", "3:4", "16:9", "9:16", "21:9", "27:16", "16:27", "9:8", "8:9"],
      resolution: ["1K", "2K", "4K"],
      background: ["transparent", "opaque", "auto"],
    },
    booleans: [],
    defaults: { resolution: "1K", aspect_ratio: "auto" },
    resolutionRatios: { "2K": ["27:16", "16:27", "9:8", "8:9"], "4K": ["27:16", "16:27", "9:8", "8:9"] },
    backgroundAt1K: true,
  },
  "gpt-image-2-5-flare-image-to-image": {
    type: "image",
    fields: ["prompt", "input_urls", "aspect_ratio", "resolution", "background"],
    required: ["prompt"],
    enums: {
      aspect_ratio: ["auto", "1:1", "3:2", "2:3", "4:3", "3:4", "16:9", "9:16", "21:9", "27:16", "16:27", "9:8", "8:9"],
      resolution: ["1K", "2K", "4K"],
      background: ["transparent", "opaque", "auto"],
    },
    booleans: [],
    defaults: { resolution: "1K", aspect_ratio: "auto" },
    imageField: "input_urls",
    maxInputImages: 16,
    resolutionRatios: { "2K": ["27:16", "16:27", "9:8", "8:9"], "4K": ["27:16", "16:27", "9:8", "8:9"] },
    backgroundAt1K: true,
  },
  "gpt-image-2-5-sunburst-text-to-image": {
    type: "image",
    fields: ["prompt", "aspect_ratio", "resolution", "background"],
    required: ["prompt"],
    enums: {
      aspect_ratio: ["auto", "1:1", "3:2", "2:3", "4:3", "3:4", "16:9", "9:16", "21:9", "27:16", "16:27", "9:8", "8:9"],
      resolution: ["1K", "2K", "4K"],
      background: ["transparent", "opaque", "auto"],
    },
    booleans: [],
    defaults: { resolution: "1K", aspect_ratio: "auto" },
    resolutionRatios: { "2K": ["27:16", "16:27", "9:8", "8:9"], "4K": ["27:16", "16:27", "9:8", "8:9"] },
    backgroundAt1K: true,
  },
  "gpt-image-2-5-sunburst-image-to-image": {
    type: "image",
    fields: ["prompt", "input_urls", "aspect_ratio", "resolution", "background"],
    required: ["prompt"],
    enums: {
      aspect_ratio: ["auto", "1:1", "3:2", "2:3", "4:3", "3:4", "16:9", "9:16", "21:9", "27:16", "16:27", "9:8", "8:9"],
      resolution: ["1K", "2K", "4K"],
      background: ["transparent", "opaque", "auto"],
    },
    booleans: [],
    defaults: { resolution: "1K", aspect_ratio: "auto" },
    imageField: "input_urls",
    maxInputImages: 16,
    resolutionRatios: { "2K": ["27:16", "16:27", "9:8", "8:9"], "4K": ["27:16", "16:27", "9:8", "8:9"] },
    backgroundAt1K: true,
  },
  "gpt-image-2-6/flare-text-to-image": {
    type: "image",
    fields: [
      "prompt",
      "aspect_ratio",
      "resolution",
      "quality",
      "background",
      "output_format",
      "complexity",
      "moderation",
      "output_compression",
      "size",
      "frame_count",
      "frame_duration_ms",
      "svg",
    ],
    required: ["prompt"],
    enums: {
      aspect_ratio: ["auto", "1:1", "3:2", "2:3", "4:3", "3:4", "5:4", "4:5", "16:9", "9:16", "2:1", "1:2", "21:9", "9:21", "3:1", "1:3"],
      resolution: ["1K", "2K", "4K"],
      quality: ["low", "medium", "high", "xhigh", "max", "auto"],
      background: ["transparent", "opaque", "auto"],
      output_format: ["png", "jpeg", "webp", "gif", "svg"],
      complexity: ["low", "medium", "high"],
      moderation: ["auto", "low"],
    },
    booleans: [],
    defaults: { aspect_ratio: "auto", resolution: "1K", quality: "medium", background: "auto", output_format: "png", complexity: "high", moderation: "low" },
    integerRanges: { output_compression: [0, 100], frame_count: [2, 16], frame_duration_ms: [20, 2000] },
    gifDefaults: { size: "auto", frame_count: 9, frame_duration_ms: 200 },
    svgModels: ["gpt-6-sol", "gpt-5.6-luna", "gpt-5.6-terra"],
    svgDefaultModel: "gpt-5.6-luna",
  },
  "gpt-image-2-6/flare-image-to-image": {
    type: "image",
    fields: [
      "prompt",
      "input_urls",
      "mask_url",
      "markup",
      "aspect_ratio",
      "resolution",
      "quality",
      "background",
      "output_format",
      "complexity",
      "moderation",
      "output_compression",
      "svg",
      "frame_count",
      "frame_duration_ms",
    ],
    required: ["prompt", "input_urls"],
    enums: {
      aspect_ratio: ["auto", "1:1", "3:2", "2:3", "4:3", "3:4", "5:4", "4:5", "16:9", "9:16", "2:1", "1:2", "21:9", "9:21", "3:1", "1:3"],
      resolution: ["1K", "2K", "4K"],
      quality: ["low", "medium", "high", "xhigh", "max", "auto"],
      background: ["transparent", "opaque", "auto"],
      output_format: ["png", "jpeg", "webp", "gif", "svg"],
      complexity: ["low", "medium", "high"],
      moderation: ["auto", "low"],
    },
    booleans: [],
    defaults: { aspect_ratio: "auto", resolution: "1K", quality: "medium", background: "auto", output_format: "png", complexity: "high", moderation: "low" },
    imageField: "input_urls",
    maxInputImages: 16,
    integerRanges: { output_compression: [0, 100], frame_count: [2, 16], frame_duration_ms: [20, 2000] },
    gifDefaults: { frame_count: 9, frame_duration_ms: 200 },
    svgModels: ["gpt-6-sol", "gpt-5.6-luna", "gpt-5.6-terra"],
    svgDefaultModel: "gpt-5.6-luna",
  },
  "gpt-image-2-6/sunburst-text-to-image": {
    type: "image",
    fields: [
      "prompt",
      "aspect_ratio",
      "resolution",
      "quality",
      "background",
      "output_format",
      "complexity",
      "moderation",
      "output_compression",
      "size",
      "frame_count",
      "frame_duration_ms",
      "svg",
    ],
    required: ["prompt"],
    enums: {
      aspect_ratio: ["auto", "1:1", "3:2", "2:3", "4:3", "3:4", "5:4", "4:5", "16:9", "9:16", "2:1", "1:2", "21:9", "9:21", "3:1", "1:3"],
      resolution: ["1K", "2K", "4K"],
      quality: ["low", "medium", "high", "xhigh", "max", "auto"],
      background: ["transparent", "opaque", "auto"],
      output_format: ["png", "jpeg", "webp", "gif", "svg"],
      complexity: ["low", "medium", "high"],
      moderation: ["auto", "low"],
    },
    booleans: [],
    defaults: { aspect_ratio: "auto", resolution: "1K", quality: "medium", background: "auto", output_format: "png", complexity: "high", moderation: "low" },
    integerRanges: { output_compression: [0, 100], frame_count: [2, 16], frame_duration_ms: [20, 2000] },
    gifDefaults: { size: "auto", frame_count: 9, frame_duration_ms: 200 },
    svgModels: ["gpt-6-sol", "gpt-5.6-luna", "gpt-5.6-terra"],
    svgDefaultModel: "gpt-5.6-luna",
  },
  "gpt-image-2-6/sunburst-image-to-image": {
    type: "image",
    fields: [
      "prompt",
      "input_urls",
      "mask_url",
      "markup",
      "aspect_ratio",
      "resolution",
      "quality",
      "background",
      "output_format",
      "complexity",
      "moderation",
      "output_compression",
      "svg",
      "frame_count",
      "frame_duration_ms",
    ],
    required: ["prompt", "input_urls"],
    enums: {
      aspect_ratio: ["auto", "1:1", "3:2", "2:3", "4:3", "3:4", "5:4", "4:5", "16:9", "9:16", "2:1", "1:2", "21:9", "9:21", "3:1", "1:3"],
      resolution: ["1K", "2K", "4K"],
      quality: ["low", "medium", "high", "xhigh", "max", "auto"],
      background: ["transparent", "opaque", "auto"],
      output_format: ["png", "jpeg", "webp", "gif", "svg"],
      complexity: ["low", "medium", "high"],
      moderation: ["auto", "low"],
    },
    booleans: [],
    defaults: { aspect_ratio: "auto", resolution: "1K", quality: "medium", background: "auto", output_format: "png", complexity: "high", moderation: "low" },
    imageField: "input_urls",
    maxInputImages: 16,
    integerRanges: { output_compression: [0, 100], frame_count: [2, 16], frame_duration_ms: [20, 2000] },
    gifDefaults: { frame_count: 9, frame_duration_ms: 200 },
    svgModels: ["gpt-6-sol", "gpt-5.6-luna", "gpt-5.6-terra"],
    svgDefaultModel: "gpt-5.6-luna",
  },
  "gpt-image-2-6/economy-text-to-image": {
    type: "image",
    fields: ["prompt", "aspect_ratio", "background", "output_format", "frame_count", "frame_duration_ms"],
    required: ["prompt"],
    enums: {
      aspect_ratio: ["auto", "1:1", "16:9", "9:16", "3:2", "2:3", "21:9", "4:3"],
      background: ["transparent", "opaque", "auto"],
      output_format: ["png", "gif"],
      frame_count: ["auto", "4", "9", "16", "25", "36", "64"],
    },
    booleans: [],
    defaults: { aspect_ratio: "auto", background: "auto", output_format: "png" },
    integerRanges: { frame_duration_ms: [20, 2000] },
    gifDefaults: { frame_count: "auto", frame_duration_ms: "auto" },
  },
  "gpt-image-2-6/economy-image-to-image": {
    type: "image",
    fields: ["prompt", "input_urls", "aspect_ratio", "background", "output_format"],
    required: ["prompt"],
    enums: {
      aspect_ratio: ["auto", "1:1", "16:9", "9:16", "3:2", "2:3", "21:9", "4:3"],
      background: ["transparent", "opaque", "auto"],
      output_format: ["png"],
    },
    booleans: [],
    defaults: { aspect_ratio: "auto", background: "auto", output_format: "png" },
    imageField: "input_urls",
    maxInputImages: 16,
  },
  "gpt-image-2-text-to-image": {
    type: "image",
    fields: ["prompt", "aspect_ratio", "resolution", "background"],
    required: ["prompt"],
    enums: {
      aspect_ratio: ["auto", "1:1", "3:2", "2:3", "4:3", "3:4", "5:4", "4:5", "16:9", "9:16", "2:1", "1:2", "3:1", "1:3", "21:9", "9:21"],
      resolution: ["1K", "2K", "4K"],
      background: ["transparent", "opaque", "auto"],
    },
    booleans: [],
    defaults: { resolution: "1K", aspect_ratio: "auto" },
    resolutionRatios: { "2K": ["5:4", "4:5", "3:1", "1:3", "9:21"], "4K": ["3:1", "1:3", "9:21"] },
    backgroundAt1K: true,
  },
  "gpt-image-2-image-to-image": {
    type: "image",
    fields: ["prompt", "input_urls", "aspect_ratio", "resolution", "background"],
    required: ["prompt"],
    enums: {
      aspect_ratio: ["auto", "1:1", "3:2", "2:3", "4:3", "3:4", "5:4", "4:5", "16:9", "9:16", "2:1", "1:2", "3:1", "1:3", "21:9", "9:21"],
      resolution: ["1K", "2K", "4K"],
      background: ["transparent", "opaque", "auto"],
    },
    booleans: [],
    defaults: { resolution: "1K", aspect_ratio: "auto" },
    imageField: "input_urls",
    maxInputImages: 16,
    resolutionRatios: { "2K": ["5:4", "4:5", "3:1", "1:3", "9:21"], "4K": ["3:1", "1:3", "9:21"] },
    backgroundAt1K: true,
  },
  "gpt-image/1.5-text-to-image": {
    type: "image",
    fields: ["prompt", "aspect_ratio", "quality"],
    required: ["prompt", "aspect_ratio", "quality"],
    enums: { aspect_ratio: ["1:1", "2:3", "3:2"], quality: ["medium", "high"] },
    booleans: [],
  },
  "gpt-image/1.5-image-to-image": {
    type: "image",
    fields: ["input_urls", "prompt", "aspect_ratio", "quality"],
    required: ["input_urls", "prompt", "aspect_ratio", "quality"],
    enums: { aspect_ratio: ["1:1", "2:3", "3:2"], quality: ["medium", "high"] },
    booleans: [],
    imageField: "input_urls",
    maxInputImages: 16,
  },
  "bytedance/seedream-v4-text-to-image": {
    type: "image",
    fields: ["prompt", "image_size", "image_resolution", "max_images", "seed", "nsfw_checker"],
    required: ["prompt"],
    defaults: { image_size: "square_hd", image_resolution: "1K", max_images: 1 },
    enums: {
      image_size: [
        "square",
        "square_hd",
        "portrait_4_3",
        "portrait_3_2",
        "portrait_16_9",
        "landscape_4_3",
        "landscape_3_2",
        "landscape_16_9",
        "landscape_21_9",
      ],
      image_resolution: ["1K", "2K", "4K"],
    },
    booleans: ["nsfw_checker"],
    maxImages: 6,
  },
  "bytedance/seedream-v4-edit": {
    type: "image",
    fields: ["prompt", "image_urls", "image_size", "image_resolution", "max_images", "seed", "nsfw_checker"],
    required: ["prompt", "image_urls"],
    defaults: { image_size: "square_hd", image_resolution: "1K", max_images: 1 },
    enums: {
      image_size: [
        "square",
        "square_hd",
        "portrait_4_3",
        "portrait_3_2",
        "portrait_16_9",
        "landscape_4_3",
        "landscape_3_2",
        "landscape_16_9",
        "landscape_21_9",
      ],
      image_resolution: ["1K", "2K", "4K"],
    },
    booleans: ["nsfw_checker"],
    imageField: "image_urls",
    maxImages: 6,
  },
  "seedream/4.5-text-to-image": {
    type: "image",
    fields: ["prompt", "aspect_ratio", "quality", "nsfw_checker"],
    required: ["prompt", "aspect_ratio", "quality"],
    enums: { aspect_ratio: ["1:1", "4:3", "3:4", "16:9", "9:16", "2:3", "3:2", "21:9"], quality: ["basic", "high"] },
    booleans: ["nsfw_checker"],
  },
  "seedream/4.5-edit": {
    type: "image",
    fields: ["prompt", "image_urls", "aspect_ratio", "quality", "nsfw_checker"],
    required: ["prompt", "image_urls", "aspect_ratio", "quality"],
    enums: { aspect_ratio: ["1:1", "4:3", "3:4", "16:9", "9:16", "2:3", "3:2", "21:9"], quality: ["basic", "high"] },
    booleans: ["nsfw_checker"],
    imageField: "image_urls",
  },
  "seedream/5-lite-text-to-image": {
    type: "image",
    fields: ["prompt", "aspect_ratio", "quality", "output_format", "nsfw_checker"],
    required: ["prompt", "aspect_ratio", "quality"],
    enums: { aspect_ratio: ["1:1", "4:3", "3:4", "16:9", "9:16", "2:3", "3:2", "21:9"], quality: ["basic", "high", "ultra"], output_format: ["png", "jpeg"] },
    booleans: ["nsfw_checker"],
  },
  "seedream/5-lite-image-to-image": {
    type: "image",
    fields: ["prompt", "image_urls", "aspect_ratio", "quality", "output_format", "nsfw_checker"],
    required: ["prompt", "image_urls", "aspect_ratio", "quality"],
    enums: { aspect_ratio: ["1:1", "4:3", "3:4", "16:9", "9:16", "2:3", "3:2", "21:9"], quality: ["basic", "high", "ultra"], output_format: ["png", "jpeg"] },
    booleans: ["nsfw_checker"],
    imageField: "image_urls",
  },
  "google/imagen4-fast": {
    type: "image",
    fields: ["prompt", "negative_prompt", "aspect_ratio", "seed"],
    required: ["prompt", "aspect_ratio"],
    enums: { aspect_ratio: ["1:1", "16:9", "9:16", "3:4", "4:3", "auto"] },
    booleans: [],
  },
  "google/imagen4-ultra": {
    type: "image",
    fields: ["prompt", "negative_prompt", "aspect_ratio", "seed"],
    required: ["prompt", "aspect_ratio"],
    enums: { aspect_ratio: ["1:1", "16:9", "9:16", "3:4", "4:3", "auto"] },
    booleans: [],
  },
  "google/imagen4": {
    type: "image",
    fields: ["prompt", "negative_prompt", "aspect_ratio", "seed"],
    required: ["prompt", "aspect_ratio"],
    enums: { aspect_ratio: ["1:1", "16:9", "9:16", "3:4", "4:3", "auto"] },
    booleans: [],
  },
  "google/nano-banana-edit": {
    type: "image",
    fields: ["prompt", "image_urls", "output_format", "aspect_ratio", "image_size"],
    required: ["prompt", "image_urls"],
    defaults: { output_format: "png", image_size: "1:1" },
    enums: {
      output_format: ["png", "jpeg"],
      aspect_ratio: ["1:1", "9:16", "16:9", "3:4", "4:3", "3:2", "2:3", "5:4", "4:5", "21:9", "auto"],
      image_size: ["1:1", "9:16", "16:9", "3:4", "4:3", "3:2", "2:3", "5:4", "4:5", "21:9", "auto"],
    },
    booleans: [],
    imageField: "image_urls",
  },
  "google/nano-banana": {
    type: "image",
    fields: ["prompt", "output_format", "aspect_ratio", "image_size", "nsfw_checker"],
    required: ["prompt"],
    defaults: { output_format: "png", image_size: "1:1" },
    enums: {
      output_format: ["png", "jpeg"],
      aspect_ratio: ["1:1", "9:16", "16:9", "3:4", "4:3", "3:2", "2:3", "5:4", "4:5", "21:9", "auto"],
      image_size: ["1:1", "9:16", "16:9", "3:4", "4:3", "3:2", "2:3", "5:4", "4:5", "21:9", "auto"],
    },
    booleans: ["nsfw_checker"],
  },
  "nano-banana-pro": {
    type: "image",
    fields: ["prompt", "image_input", "aspect_ratio", "resolution", "output_format"],
    required: ["prompt"],
    defaults: { aspect_ratio: "1:1", resolution: "1K" },
    enums: {
      aspect_ratio: ["1:1", "2:3", "3:2", "3:4", "4:3", "4:5", "5:4", "9:16", "16:9", "21:9", "auto"],
      resolution: ["1K", "2K", "4K"],
      output_format: ["png", "jpg"],
    },
    booleans: [],
    imageField: "image_input",
  },
  "nano-banana-2": {
    type: "image",
    fields: ["prompt", "image_input", "aspect_ratio", "resolution", "output_format"],
    required: ["prompt"],
    defaults: { aspect_ratio: "auto", resolution: "1K", output_format: "jpg" },
    enums: {
      aspect_ratio: ["1:1", "2:3", "3:2", "1:4", "4:1", "3:4", "4:3", "4:5", "5:4", "1:8", "8:1", "9:16", "16:9", "21:9", "auto"],
      resolution: ["1K", "2K", "4K"],
      output_format: ["png", "jpg"],
    },
    booleans: [],
    imageField: "image_input",
  },
  "nano-banana-2-1": {
    type: "image",
    fields: ["prompt", "image_input", "aspect_ratio", "resolution", "output_format"],
    required: ["prompt"],
    defaults: { aspect_ratio: "auto", resolution: "1K", output_format: "jpg" },
    enums: {
      aspect_ratio: ["1:1", "2:3", "3:2", "1:4", "4:1", "3:4", "4:3", "4:5", "5:4", "1:8", "8:1", "9:16", "16:9", "21:9", "auto"],
      resolution: ["1K", "2K", "4K"],
      output_format: ["png", "jpg"],
    },
    booleans: [],
    imageField: "image_input",
  },
  "nano-banana-2-lite": {
    type: "image",
    fields: ["image_urls", "prompt", "aspect_ratio"],
    required: ["prompt", "aspect_ratio"],
    defaults: { image_urls: [] },
    enums: { aspect_ratio: ["1:1", "1:4", "1:8", "2:3", "3:2", "3:4", "4:1", "4:3", "4:5", "5:4", "8:1", "9:16", "16:9", "21:9", "auto"] },
    booleans: [],
    imageField: "image_urls",
  },
  "flux-2/pro-text-to-image": {
    type: "image",
    fields: ["prompt", "aspect_ratio", "resolution", "nsfw_checker"],
    required: ["prompt", "aspect_ratio", "resolution"],
    enums: { aspect_ratio: ["1:1", "4:3", "3:4", "16:9", "9:16", "3:2", "2:3"], resolution: ["1K", "2K"] },
    booleans: ["nsfw_checker"],
  },
  "flux-2/pro-image-to-image": {
    type: "image",
    fields: ["input_urls", "prompt", "aspect_ratio", "resolution", "nsfw_checker"],
    required: ["input_urls", "prompt", "aspect_ratio", "resolution"],
    enums: { aspect_ratio: ["1:1", "4:3", "3:4", "16:9", "9:16", "3:2", "2:3", "auto"], resolution: ["1K", "2K"] },
    booleans: ["nsfw_checker"],
    imageField: "input_urls",
  },
  "flux-2/flex-image-to-image": {
    type: "image",
    fields: ["input_urls", "prompt", "aspect_ratio", "resolution", "nsfw_checker"],
    required: ["input_urls", "prompt", "aspect_ratio", "resolution"],
    enums: { aspect_ratio: ["1:1", "4:3", "3:4", "16:9", "9:16", "3:2", "2:3", "auto"], resolution: ["1K", "2K"] },
    booleans: ["nsfw_checker"],
    imageField: "input_urls",
  },
  "flux-2/flex-text-to-image": {
    type: "image",
    fields: ["prompt", "aspect_ratio", "resolution", "nsfw_checker"],
    required: ["prompt", "aspect_ratio", "resolution"],
    enums: { aspect_ratio: ["1:1", "4:3", "3:4", "16:9", "9:16", "3:2", "2:3"], resolution: ["1K", "2K"] },
    booleans: ["nsfw_checker"],
  },
  "grok-imagine/text-to-image": {
    type: "image",
    fields: ["prompt", "aspect_ratio", "nsfw_checker", "enable_pro"],
    required: ["prompt", "aspect_ratio"],
    defaults: { enable_pro: false },
    enums: { aspect_ratio: ["2:3", "3:2", "1:1", "16:9", "9:16"] },
    booleans: ["nsfw_checker", "enable_pro"],
  },
  "grok-imagine/image-to-image": {
    type: "image",
    fields: ["prompt", "image_urls", "nsfw_checker"],
    required: ["image_urls"],
    enums: {},
    booleans: ["nsfw_checker"],
    imageField: "image_urls",
  },
  "grok-imagine/text-to-video": {
    type: "video",
    fields: ["prompt", "aspect_ratio", "mode", "duration", "resolution", "nsfw_checker"],
    required: ["prompt"],
    defaults: { aspect_ratio: "2:3", mode: "normal", resolution: "480p", duration: 6 },
    enums: { aspect_ratio: ["2:3", "3:2", "1:1", "16:9", "9:16"], mode: ["fun", "normal", "spicy"], resolution: ["480p", "720p", "1080p"] },
    booleans: ["nsfw_checker"],
    durationRange: [6, 30],
  },
  "grok-imagine/image-to-video": {
    type: "video",
    fields: ["image_urls", "task_id", "index", "prompt", "mode", "duration", "resolution", "aspect_ratio"],
    required: [],
    defaults: { index: 0, mode: "normal", resolution: "480p", aspect_ratio: "16:9", duration: "6" },
    enums: { mode: ["fun", "normal", "spicy"], resolution: ["480p", "720p", "1080p"], aspect_ratio: ["2:3", "3:2", "1:1", "16:9", "9:16"] },
    booleans: [],
    imageField: "image_urls",
    durationRange: [6, 30],
  },
  "kling-2.6/text-to-video": {
    type: "video",
    fields: ["prompt", "sound", "aspect_ratio", "duration"],
    required: ["prompt", "sound", "aspect_ratio", "duration"],
    defaults: { duration: "5" },
    enums: { aspect_ratio: ["1:1", "16:9", "9:16"], duration: ["5", "10"] },
    booleans: ["sound"],
  },
  "kling-2.6/image-to-video": {
    type: "video",
    fields: ["prompt", "image_urls", "sound", "duration"],
    required: ["prompt", "image_urls", "sound", "duration"],
    defaults: { duration: "5" },
    enums: { duration: ["5", "10"] },
    booleans: ["sound"],
    imageField: "image_urls",
  },
  "kling/v2-5-turbo-image-to-video-pro": {
    type: "video",
    fields: ["prompt", "image_url", "tail_image_url", "duration", "negative_prompt", "cfg_scale"],
    required: ["prompt", "image_url", "duration"],
    defaults: { cfg_scale: 0.5, duration: "5" },
    enums: { duration: ["5", "10"] },
    booleans: [],
    imageField: "image_url",
  },
  "kling/v2-5-turbo-text-to-video-pro": {
    type: "video",
    fields: ["prompt", "duration", "aspect_ratio", "negative_prompt", "cfg_scale"],
    required: ["prompt", "duration"],
    defaults: { aspect_ratio: "16:9", cfg_scale: 0.5, duration: "5" },
    enums: { duration: ["5", "10"], aspect_ratio: ["16:9", "9:16", "1:1"] },
    booleans: [],
  },
  "kling/v2-1-master-image-to-video": {
    type: "video",
    fields: ["prompt", "image_url", "duration", "negative_prompt", "cfg_scale"],
    required: ["prompt", "image_url", "duration"],
    defaults: { cfg_scale: 0.5, duration: "5" },
    enums: { duration: ["5", "10"] },
    booleans: [],
    imageField: "image_url",
  },
  "kling/v2-1-master-text-to-video": {
    type: "video",
    fields: ["prompt", "duration", "aspect_ratio", "negative_prompt", "cfg_scale"],
    required: ["prompt", "duration"],
    defaults: { aspect_ratio: "16:9", cfg_scale: 0.5, duration: "5" },
    enums: { duration: ["5", "10"], aspect_ratio: ["16:9", "9:16", "1:1"] },
    booleans: [],
  },
  "bytedance/v1-pro-fast-image-to-video": {
    type: "video",
    fields: ["prompt", "image_url", "resolution", "duration", "nsfw_checker"],
    required: ["prompt", "image_url"],
    defaults: { resolution: "720p", duration: "5" },
    enums: { resolution: ["720p", "1080p"], duration: ["5", "10"] },
    booleans: ["nsfw_checker"],
    imageField: "image_url",
  },
  "bytedance/v1-pro-image-to-video": {
    type: "video",
    fields: ["prompt", "image_url", "resolution", "duration", "camera_fixed", "seed", "enable_safety_checker", "nsfw_checker"],
    required: ["prompt", "image_url"],
    defaults: { resolution: "720p", duration: "5", seed: -1 },
    enums: { resolution: ["480p", "720p", "1080p"], duration: ["5", "10"] },
    booleans: ["camera_fixed", "enable_safety_checker", "nsfw_checker"],
    imageField: "image_url",
  },
  "hailuo/2-3-image-to-video-pro": {
    max1080Duration: 6,
    type: "video",
    fields: ["prompt", "image_url", "duration", "resolution", "nsfw_checker"],
    required: ["prompt", "image_url", "duration", "resolution"],
    defaults: { duration: "6" },
    enums: { duration: ["6", "10"], resolution: ["768P", "1080P"] },
    booleans: ["nsfw_checker"],
    imageField: "image_url",
  },
  "hailuo/2-3-image-to-video-standard": {
    max1080Duration: 6,
    type: "video",
    fields: ["prompt", "image_url", "duration", "resolution", "nsfw_checker"],
    required: ["prompt", "image_url", "duration", "resolution"],
    defaults: { duration: "6" },
    enums: { duration: ["6", "10"], resolution: ["768P", "1080P"] },
    booleans: ["nsfw_checker"],
    imageField: "image_url",
  },
  "wan/2-6-image-to-video": {
    type: "video",
    fields: ["prompt", "image_urls", "duration", "resolution", "multi_shots", "nsfw_checker"],
    required: ["prompt", "image_urls"],
    defaults: { duration: "5", resolution: "1080p", multi_shots: false },
    enums: { duration: ["5", "10", "15"], resolution: ["720p", "1080p"] },
    booleans: ["multi_shots", "nsfw_checker"],
    imageField: "image_urls",
  },
  "wan/2-6-text-to-video": {
    type: "video",
    fields: ["prompt", "duration", "resolution", "multi_shots", "nsfw_checker"],
    required: ["prompt"],
    defaults: { duration: "5", multi_shots: false },
    enums: { duration: ["5", "10", "15"], resolution: ["720p", "1080p"] },
    booleans: ["multi_shots", "nsfw_checker"],
  },
  "wan/2-6-video-to-video": {
    type: "video",
    fields: ["prompt", "video_urls", "duration", "resolution", "multi_shots", "nsfw_checker"],
    required: ["prompt", "video_urls"],
    defaults: { duration: "5", multi_shots: false },
    enums: { duration: ["5", "10"], resolution: ["720p", "1080p"] },
    booleans: ["multi_shots", "nsfw_checker"],
    videoField: "video_urls",
  },
  "wan/2-5-image-to-video": {
    type: "video",
    fields: ["prompt", "image_url", "duration", "resolution", "negative_prompt", "enable_prompt_expansion", "seed", "nsfw_checker"],
    required: ["prompt", "image_url", "duration", "resolution"],
    defaults: { duration: "5" },
    enums: { duration: ["5", "10"], resolution: ["720p", "1080p"] },
    booleans: ["enable_prompt_expansion", "nsfw_checker"],
    imageField: "image_url",
  },
  "wan/2-5-text-to-video": {
    type: "video",
    fields: ["prompt", "duration", "aspect_ratio", "resolution", "negative_prompt", "enable_prompt_expansion", "seed", "nsfw_checker"],
    required: ["prompt", "duration", "resolution"],
    defaults: { duration: "5" },
    enums: { duration: ["5", "10"], aspect_ratio: ["16:9", "9:16", "1:1"], resolution: ["720p", "1080p"] },
    booleans: ["enable_prompt_expansion", "nsfw_checker"],
  },
};

// Image models keep one identity across generations and edits.
// The canonical request records the operation; driver hooks never inspect paths.
const IMAGE_FAMILIES = {
  "google/nano-banana": { generate: "google/nano-banana", edit: "google/nano-banana-edit" },
  "gpt-image-1.5": { generate: "gpt-image/1.5-text-to-image", edit: "gpt-image/1.5-image-to-image" },
  "gpt-image-2": { generate: "gpt-image-2-text-to-image", edit: "gpt-image-2-image-to-image" },
  "gpt-image-2.5-flare": { generate: "gpt-image-2-5-flare-text-to-image", edit: "gpt-image-2-5-flare-image-to-image" },
  "gpt-image-2.5-sunburst": { generate: "gpt-image-2-5-sunburst-text-to-image", edit: "gpt-image-2-5-sunburst-image-to-image" },
  "gpt-image-2.6-flare": { generate: "gpt-image-2-6/flare-text-to-image", edit: "gpt-image-2-6/flare-image-to-image" },
  "gpt-image-2.6-sunburst": { generate: "gpt-image-2-6/sunburst-text-to-image", edit: "gpt-image-2-6/sunburst-image-to-image" },
  "gpt-image-2.6-economy": { generate: "gpt-image-2-6/economy-text-to-image", edit: "gpt-image-2-6/economy-image-to-image" },
};
const LEGACY_IMAGE_MODELS = {};
for (const model of Object.keys(IMAGE_FAMILIES)) {
  for (const operation of ["generate", "edit"]) {
    LEGACY_IMAGE_MODELS[IMAGE_FAMILIES[model][operation]] = { model: model, operation: operation };
  }
}
const MODEL_NAMES = Object.keys(MODELS)
  .filter(function (model) {
    return !Object.hasOwn(LEGACY_IMAGE_MODELS, model);
  })
  .concat(Object.keys(IMAGE_FAMILIES));

const IMAGE_COUNT = {
  type: "number",
  unit: "count",
  unitLabel: { en: "image", zh: "张", "zh-TW": "張" },
  description: { en: "Image generation unit price", zh: "图片生成单价" },
};
const SECONDS = { type: "number", unit: "second", description: { en: "Video generation unit price", zh: "视频生成单价" } };
const REQUESTS = { type: "number", unit: "count", description: { en: "Generation request unit price", zh: "生成请求单价" } };
const USAGE_DESCRIPTIONS = {
  resolution: { en: "Output resolution", zh: "输出分辨率" },
  image_resolution: { en: "Output image resolution", zh: "输出图片分辨率" },
  quality: { en: "Output image quality", zh: "输出图片质量" },
  sound: { en: "Whether audio is generated", zh: "是否生成音频" },
  enable_pro: { en: "Quality mode enabled", zh: "启用质量模式" },
};

function usageSchema(spec) {
  const schema = { requests: REQUESTS };
  schema[spec.type === "image" ? "image_count" : "seconds"] = spec.type === "image" ? IMAGE_COUNT : SECONDS;
  for (const key of Object.keys(USAGE_DESCRIPTIONS)) {
    if (!spec.fields.includes(key)) continue;
    schema[key] = spec.booleans.includes(key)
      ? { type: "boolean", description: USAGE_DESCRIPTIONS[key] }
      : {
          enum: ["unspecified"].concat(spec.enums[key] || []),
          enumLabels: { unspecified: { en: "Provider default", zh: "厂商默认值" } },
          description: USAGE_DESCRIPTIONS[key],
        };
  }
  return schema;
}

export const meta = {
  apiVersion: 1,
  key: "kie",
  name: "Kie AI",
  icon: "text:Kie",
  description: { en: "Kie AI image and video generation through the Market API", zh: "Kie AI Market 图片与视频生成" },
  version: "1.0.0",
  author: { name: "QuantumNous" },
  website: "https://kie.ai",
  baseUrl: "https://api.kie.ai",
  keyHint: { en: "Kie AI API key", zh: "Kie AI API 密钥" },
  models: MODEL_NAMES,
  fetchMode: "per_task",
  upstreams: ["vendor", "new_api"],
  // Hidden legacy image tasks still settle their measured image count.
  usageSchema: { requests: REQUESTS, image_count: IMAGE_COUNT },
  usageProfiles: MODEL_NAMES.map(function (model) {
    return { models: [model], schema: usageSchema(modelSpec({ model: model })) };
  }),
  routes: [
    { method: "POST", path: "/api/v1/jobs/createTask", type: "submit", decode: "createTask", render: "taskCreated" },
    { method: "GET", path: "/api/v1/jobs/recordInfo", type: "query", taskIdParam: "taskId", render: "taskStatus" },
  ],
  protocols: [
    { name: "openai_responses", supports: ["stream", "sync", "background"] },
    {
      name: "openai_image",
      models: MODEL_NAMES.filter(function (model) {
        return modelSpec({ model: model }).type === "image";
      }),
    },
    {
      name: "openai_video",
      models: Object.keys(MODELS).filter(function (model) {
        return MODELS[model].type === "video";
      }),
    },
  ],
};

function object(value) {
  return value !== null && typeof value === "object" && !Array.isArray(value) ? value : null;
}

function text(value) {
  return typeof value === "string" ? value.trim() : "";
}

function vendorModel(ctx) {
  const model = text(ctx.upstreamModel || ctx.model);
  if (!Object.hasOwn(IMAGE_FAMILIES, model)) return model;
  const operation = (ctx.requestBody || {}).operation || "generate";
  if (operation !== "generate" && operation !== "edit") throw new Error("Unsupported image operation");
  return IMAGE_FAMILIES[model][operation];
}

function modelSpec(ctx) {
  const model = vendorModel(ctx);
  const spec = Object.hasOwn(MODELS, model) ? MODELS[model] : null;
  if (!spec) throw new Error("Unsupported Kie model: " + model);
  if (
    Object.hasOwn(IMAGE_FAMILIES, text(ctx.upstreamModel || ctx.model)) &&
    (ctx.requestBody || {}).operation === "edit" &&
    !spec.required.includes(spec.imageField)
  )
    return Object.assign({}, spec, { required: spec.required.concat(spec.imageField) });
  return spec;
}

function jsonBody(ctx) {
  if (!ctx.body || ctx.body.kind !== "json" || !object(ctx.body.value)) throw new Error("Kie requires a JSON object with publicly accessible media URLs");
  return ctx.body.value;
}

function httpURL(value) {
  return typeof value === "string" && /^https?:\/\/[^\s]+$/i.test(value);
}

// All surfaces and both billing hooks use the exact normalized vendor input.
// Client metadata is merged before this validation, never after reservation.
function normalizeInput(spec, value) {
  if (!object(value)) throw new Error("input must be an object");
  const input = Object.assign({}, spec.defaults || {});
  for (const key of Object.keys(value)) {
    if (!spec.fields.includes(key)) throw new Error("Unsupported Kie input field: " + key);
    input[key] = value[key];
  }
  if (spec.svgModels && input.output_format === "jpg") input.output_format = "jpeg";
  if (spec.gifDefaults && input.output_format === "gif") {
    for (const key of Object.keys(spec.gifDefaults)) {
      if (input[key] === undefined) input[key] = spec.gifDefaults[key];
    }
  }
  for (const key of Object.keys(spec.integerRanges || {})) {
    if (input[key] === undefined) continue;
    if (key === "frame_duration_ms" && input[key] === "auto" && spec.gifDefaults && spec.gifDefaults[key] === "auto") continue;
    const bounds = spec.integerRanges[key];
    if (!Number.isInteger(input[key]) || input[key] < bounds[0] || input[key] > bounds[1])
      throw new Error("input." + key + " must be an integer from " + bounds[0] + " to " + bounds[1]);
  }
  const unsupportedRatios = spec.resolutionRatios && spec.resolutionRatios[input.resolution];
  if (unsupportedRatios && unsupportedRatios.includes(input.aspect_ratio)) throw new Error("Unsupported aspect ratio for this resolution");
  if (spec.backgroundAt1K && input.background !== undefined && input.resolution !== "1K") throw new Error("background is supported only at 1K");
  if (spec.svgModels) {
    if (input.output_compression !== undefined && !["jpeg", "webp"].includes(input.output_format))
      throw new Error("output_compression requires jpeg or webp output");
    if (input.background === "transparent" && !["png", "webp", "gif"].includes(input.output_format))
      throw new Error("Transparent backgrounds require png, webp or gif output");
    if (input.mask_url && input.markup) throw new Error("mask_url and markup cannot be combined");
    for (const key of ["mask_url", "markup"]) {
      if (input[key] !== undefined && !httpURL(input[key])) throw new Error("input." + key + " must be an HTTP URL");
    }
    if (input.mask_url && ["gif", "svg"].includes(input.output_format)) throw new Error("mask_url is not supported for gif or svg output");
    if (input.output_format === "svg") {
      const svg = input.svg === undefined ? {} : object(input.svg);
      if (
        !svg ||
        Object.keys(svg).some(function (key) {
          return key !== "model";
        })
      )
        throw new Error("svg must contain only an author model");
      const authorModel = svg.model === undefined ? spec.svgDefaultModel : svg.model;
      if (!spec.svgModels.includes(authorModel)) throw new Error("Unsupported SVG author model");
      input.svg = { model: authorModel };
    } else if (input.svg !== undefined) throw new Error("svg requires SVG output");
    if (input.output_format === "gif" && spec.fields.includes("size")) {
      const size = input.size === "auto" ? ["512", "512"] : typeof input.size === "string" ? input.size.split("x") : [];
      const width = Number(size[0]);
      const height = Number(size[1]);
      if (size.length !== 2 || !Number.isInteger(width) || !Number.isInteger(height) || width <= 0 || height <= 0 || width % 16 || height % 16)
        throw new Error("GIF size must have positive dimensions divisible by 16");
      const frames = input.frame_count;
      const columns = frames <= 8 ? 4 : frames <= 9 ? 3 : 4;
      const rows = frames <= 8 ? 2 : frames <= 9 ? 3 : frames <= 12 ? 3 : 4;
      const fits =
        (width * columns <= 3840 && height * rows <= 3840 && Math.max(width * columns, height * rows) <= 3 * Math.min(width * columns, height * rows)) ||
        (width * rows <= 3840 && height * columns <= 3840 && Math.max(width * rows, height * columns) <= 3 * Math.min(width * rows, height * columns));
      if (!fits || width * height * columns * rows > 8294400) throw new Error("GIF sprite sheet exceeds supported dimensions");
    } else if (input.size !== undefined) throw new Error("size is supported only for GIF output");
  }
  for (const key of spec.required) {
    const fieldValue = input[key];
    if (fieldValue === undefined || fieldValue === null || fieldValue === "" || (Array.isArray(fieldValue) && fieldValue.length === 0))
      throw new Error("input." + key + " is required");
  }
  for (const key of spec.booleans) {
    if (input[key] !== undefined && typeof input[key] !== "boolean") throw new Error("input." + key + " must be a boolean");
  }
  // Bound durations before any arithmetic, preserving the vendor's wire type.
  if (spec.type === "video") {
    const duration = input.duration;
    if (!((typeof duration === "string" && /^\d+$/.test(duration)) || typeof duration === "number"))
      throw new Error("input.duration must be a positive integer");
    const seconds = Number(duration);
    const limits = spec.durationRange || [1, 3600];
    if (!Number.isInteger(seconds) || seconds < limits[0] || seconds > limits[1]) throw new Error("input.duration is outside the supported range");
    input.duration = typeof spec.defaults.duration === "number" ? seconds : String(seconds);
  }
  if (spec.maxImages) {
    if (!Number.isInteger(input.max_images) || input.max_images < 1 || input.max_images > spec.maxImages)
      throw new Error("input.max_images must be an integer from 1 to " + spec.maxImages);
  }
  for (const key of Object.keys(spec.enums)) {
    if (input[key] !== undefined && !spec.enums[key].includes(input[key])) throw new Error("Unsupported input." + key);
  }
  for (const key of [spec.imageField, spec.videoField, "tail_image_url"].filter(Boolean)) {
    if (input[key] === undefined) continue;
    const urls = key.endsWith("_url") ? [input[key]] : input[key];
    if (
      !Array.isArray(urls) ||
      urls.length > (key === spec.imageField ? spec.maxInputImages || 128 : 128) ||
      urls.some(function (url) {
        return !httpURL(url);
      })
    )
      throw new Error("input." + key + " must contain publicly accessible HTTP URLs");
  }
  if (spec.type === "video" && spec.imageField && !input[spec.imageField] && !text(input.task_id)) throw new Error("An input image is required");
  if (spec.type === "video" && spec.imageField && Array.isArray(input[spec.imageField]) && input[spec.imageField].length === 0 && !text(input.task_id))
    throw new Error("An input image is required");
  if (spec.videoField && (!Array.isArray(input[spec.videoField]) || input[spec.videoField].length === 0)) throw new Error("An input video is required");
  if (
    spec.type === "video" &&
    input.resolution === "1080P" &&
    Number(input.duration) === 10 &&
    spec.fields.includes("nsfw_checker") &&
    spec.imageField === "image_url"
  )
    throw new Error("This model does not support 10 seconds at 1080P");
  if (input.prompt !== undefined && !text(input.prompt)) throw new Error("input.prompt must be a non-empty string");
  return input;
}

function submitIntent(ctx, body, operation) {
  let model = text(ctx.model || body.model);
  if (!model) throw new Error("model is required");
  // Native Kie requests may still carry the provider's split model names.
  if (!text(ctx.model) && Object.hasOwn(LEGACY_IMAGE_MODELS, model) && LEGACY_IMAGE_MODELS[model].model !== model) {
    operation = LEGACY_IMAGE_MODELS[model].operation;
    model = LEGACY_IMAGE_MODELS[model].model;
  }
  const family = IMAGE_FAMILIES[text(ctx.upstreamModel || model)];
  const unified = Object.hasOwn(IMAGE_FAMILIES, text(ctx.upstreamModel || model));
  if (unified && operation === undefined) {
    const imageField = MODELS[family.edit].imageField;
    operation = object(body.input) && body.input[imageField] !== undefined ? "edit" : "generate";
  }
  const requestBody = { model: model, input: body.input };
  if (unified) requestBody.operation = operation;
  const spec = modelSpec({ model: model, upstreamModel: ctx.upstreamModel, requestBody: requestBody });
  const input = normalizeInput(spec, body.input);
  requestBody.input = input;
  const intent = { kind: "submit", model: model, action: spec.type, requestBody: requestBody };
  if (text(input.task_id)) intent.originTaskIds = [input.task_id];
  return intent;
}

function apiRoot(ctx) {
  return ctx.baseUrl.replace(/\/+$/, "") + (ctx.upstream && ctx.upstream.kind === "new_api" ? "/kie" : "");
}

function authorization(ctx) {
  if (text(ctx.apiKey)) return "Bearer " + ctx.apiKey;
  return text(ctx.authHeader);
}

function responseData(body) {
  if (!object(body) || body.code !== 200) throw new Error("Kie API error: " + (text(body && body.msg) || "invalid response"));
  if (!object(body.data)) throw new Error("Kie returned invalid task data");
  return body.data;
}

export function buildSubmitRequest(ctx) {
  const spec = modelSpec(ctx);
  const input = normalizeInput(spec, (ctx.requestBody || {}).input);
  if (text(input.task_id)) {
    const origin = (ctx.originTasks || []).find(function (task) {
      return task.taskId === input.task_id;
    });
    if (!origin || !text(origin.upstreamTaskId)) throw new Error("Referenced Kie task is unavailable");
    input.task_id = origin.upstreamTaskId;
  }
  return {
    url: apiRoot(ctx) + "/api/v1/jobs/createTask",
    method: "POST",
    headers: { Authorization: authorization(ctx), "Content-Type": "application/json", Accept: "application/json" },
    body: { model: ctx.upstream && ctx.upstream.kind === "new_api" ? ctx.upstreamModel || ctx.model : vendorModel(ctx), input: input },
    action: spec.type,
  };
}

export function parseSubmitResponse(ctx, response) {
  const data = responseData(response.body);
  const id = text(data.taskId);
  if (!id) throw new Error("Kie did not return a taskId");
  return { taskId: id, taskData: response.body };
}

export function extractUsage(ctx) {
  if (ctx.usagePurpose === "billing_ratios") return null;
  const spec = modelSpec(ctx);
  const input = normalizeInput(spec, (ctx.requestBody || {}).input);
  const facts = { requests: 1 };
  if (spec.type === "image") facts.image_count = spec.maxImages ? input.max_images : 1;
  else facts.seconds = Number(input.duration);
  for (const key of Object.keys(USAGE_DESCRIPTIONS)) {
    if (!spec.fields.includes(key)) continue;
    facts[key] = spec.booleans.includes(key) ? input[key] === true : input[key] === undefined ? "unspecified" : input[key];
  }
  return facts;
}

export function buildQueryRequest(ctx) {
  return {
    url: apiRoot(ctx) + "/api/v1/jobs/recordInfo?taskId=" + encodeURIComponent(ctx.taskId),
    method: "GET",
    headers: { Authorization: authorization(ctx), Accept: "application/json" },
  };
}

// resultJson is JSON text; newer replies also provide its parsed `response`.
function resultURLs(data) {
  const envelope = object(data);
  const task = envelope && object(envelope.data);
  if (!task) return [];
  const result = text(task.resultJson) ? object(JSON.parse(task.resultJson)) : object(task.response);
  return result && Array.isArray(result.resultUrls) ? result.resultUrls.filter(httpURL) : [];
}

export function parseTaskResult(ctx, body) {
  const data = responseData(body);
  const statuses = { waiting: "NOT_START", queuing: "QUEUED", generating: "IN_PROGRESS", success: "SUCCESS", fail: "FAILURE" };
  const status = Object.hasOwn(statuses, data.state) ? statuses[data.state] : "UNKNOWN";
  const result = { status: status };
  if (status === "FAILURE") result.reason = text(data.failMsg) || "Kie generation failed";
  if (status === "UNKNOWN") result.reason = "Unrecognized Kie task state";
  if (status === "SUCCESS") {
    const urls = resultURLs(body);
    if (!urls.length) throw new Error("Kie completed without a valid media result");
    result.url = urls[0];
  }
  if (typeof data.progress === "number" && Number.isFinite(data.progress) && data.progress >= 0 && data.progress <= 100) result.progress = data.progress + "%";
  return result;
}

export function extractUsageOnComplete(ctx, result, body) {
  if (!body || !object(body.data) || body.data.state !== "success") return null;
  const spec = modelSpec(ctx);
  if (spec.type !== "image") return null;
  const count = resultURLs(body).length;
  // Invalid counts keep the reserved request quantity. costTime is processing
  // latency, not generated video duration; never use it to settle seconds.
  return Number.isInteger(count) && count > 0 && count <= 128 ? { image_count: count } : null;
}

function nativeTaskData(task) {
  const envelope = object(task.data);
  const data = envelope && object(envelope.data);
  const states = { NOT_START: "waiting", SUBMITTED: "waiting", QUEUED: "queuing", IN_PROGRESS: "generating", SUCCESS: "success", FAILURE: "fail" };
  // Rebuild taskId explicitly; the raw provider task id never reaches clients.
  const output = Object.assign({}, data || {}, { taskId: task.task_id, state: states[task.status] || "waiting" });
  if (task.status === "FAILURE") output.failMsg = task.fail_reason || text(output.failMsg) || "Kie generation failed";
  // Original request parameters may contain private origin task ids or callbacks.
  delete output.param;
  return output;
}

export const native = {
  createTask: function (ctx) {
    return submitIntent(ctx, jsonBody(ctx));
  },
  taskCreated: function (ctx, task) {
    return { code: 200, msg: "success", data: { taskId: task.task_id } };
  },
  taskStatus: function (ctx, task) {
    return { code: 200, msg: "success", data: nativeTaskData(task) };
  },
  error: function (ctx, error) {
    return { code: error.httpStatus || 400, msg: error.message };
  },
};

export function listArtifacts(task) {
  if (task.status !== "SUCCESS") return [];
  const type = task.action === "video" ? "video" : "image";
  return resultURLs(task.data).map(function (_url, index) {
    return { key: "media_" + index, type: type };
  });
}

export function buildContentRequest(ctx) {
  const match = /^media_(\d+)$/.exec(ctx.artifactKey || "");
  const url = match && resultURLs(ctx.data)[Number(match[1])];
  if (!url) throw new Error("artifact_not_found");
  return { url: url, method: ctx.clientRequest.method, credentialless: true };
}

// Standard protocol fields are mapped to the model's documented input names.
// Vendor-only parameters go in metadata; explicit protocol fields win.
function protocolIntent(ctx, protocol) {
  const req = jsonBody(ctx);
  const model = text(ctx.model || req.model);
  if (req.metadata !== undefined && !object(req.metadata)) throw new Error("metadata must be an object");
  const input = Object.assign({}, object(req.metadata) || {});
  const images = [];
  const texts = [];
  if (protocol === "responses") {
    if (typeof req.input === "string") texts.push(req.input);
    else if (Array.isArray(req.input)) {
      for (const item of req.input) {
        if (typeof item === "string") {
          texts.push(item);
          continue;
        }
        if (!object(item)) throw new Error("Unsupported Responses input item");
        const parts = item.content === undefined ? [item] : Array.isArray(item.content) ? item.content : [item.content];
        for (const part of parts) {
          if (typeof part === "string") {
            texts.push(part);
            continue;
          }
          if (!object(part)) throw new Error("Unsupported Responses content");
          if (["input_text", "text"].includes(part.type) && typeof part.text === "string") texts.push(part.text);
          else if (["input_image", "image_url"].includes(part.type))
            images.push(typeof part.image_url === "string" ? part.image_url : (part.image_url || {}).url);
          else throw new Error("Unsupported Responses content type");
        }
      }
    } else if (req.input !== undefined) throw new Error("input must be a string or array");
  }
  for (const value of [req.image, req.input_reference].concat(Array.isArray(req.images) ? req.images : [])) {
    if (value !== undefined) images.push(typeof value === "string" ? value : (value || {}).url);
  }
  const unified = Object.hasOwn(IMAGE_FAMILIES, text(ctx.upstreamModel || model));
  let operation;
  if (unified) {
    if (protocol === "image") operation = ctx.operation || "generate";
    else {
      const imageField = MODELS[IMAGE_FAMILIES[text(ctx.upstreamModel || model)].edit].imageField;
      operation = images.length || input[imageField] !== undefined || req[imageField] !== undefined ? "edit" : "generate";
    }
    if (operation !== "generate" && operation !== "edit") throw new Error("Unsupported image operation");
  }
  const spec = modelSpec({ model: model, upstreamModel: ctx.upstreamModel, requestBody: { operation: operation } });
  if ((protocol === "image" && spec.type !== "image") || (protocol === "video" && spec.type !== "video"))
    throw new Error("This Kie model does not support the requested protocol");
  if (text(req.prompt)) input.prompt = req.prompt;
  else if (texts.length) input.prompt = texts.join("\n");
  for (const key of spec.fields) {
    if (key !== "size" && req[key] !== undefined) input[key] = req[key];
  }
  if (images.length) {
    if (!spec.imageField) throw new Error("This Kie model does not accept image input");
    if (spec.imageField.endsWith("_url") && images.length !== 1) throw new Error("This Kie model accepts exactly one input image");
    input[spec.imageField] = spec.imageField.endsWith("_url") ? images[0] : images;
  }
  if (protocol === "image" && ctx.operation === "edit" && (!spec.imageField || !input[spec.imageField] || input[spec.imageField].length === 0))
    throw new Error("An input image URL is required for image edits");
  if (req.n !== undefined) {
    if (!Number.isInteger(req.n) || req.n < 1 || req.n > (spec.maxImages || 1)) throw new Error("Unsupported image count for this Kie model");
    if (spec.maxImages) input.max_images = req.n;
  }
  if (req.seconds !== undefined) input.duration = req.seconds;
  if (req.size !== undefined && req.size !== "auto") {
    const ratios = { "1024x1024": "1:1", "1536x1024": "3:2", "1024x1536": "2:3", "1280x720": "16:9", "720x1280": "9:16" };
    if (input.output_format === "gif" && spec.fields.includes("size")) input.size = req.size;
    else if (spec.fields.includes("aspect_ratio") && ratios[req.size]) input.aspect_ratio = ratios[req.size];
    else if (spec.enums.resolution && spec.enums.resolution.includes(req.size)) input.resolution = req.size;
    else if (spec.enums.image_resolution && spec.enums.image_resolution.includes(req.size)) input.image_resolution = req.size;
    else throw new Error("Unsupported size for this Kie model; use metadata for vendor parameters");
  }
  // Set required standard options explicitly so billing and the vendor agree.
  for (const key of ["aspect_ratio", "quality", "resolution"]) {
    if (input[key] === undefined && spec.required.includes(key) && spec.enums[key]) input[key] = spec.enums[key][0];
  }
  if (input.sound === undefined && spec.fields.includes("sound")) input.sound = false;
  return submitIntent({ model: model, upstreamModel: ctx.upstreamModel }, { input: input }, operation);
}

function responseOutput(ctx) {
  const artifacts = Object.values(ctx.artifacts || {});
  if (!artifacts.length) throw new Error("Kie media artifacts are unavailable");
  return artifacts
    .map(function (artifact) {
      const url = text(artifact.url).replace(/&/g, "&amp;").replace(/"/g, "&quot;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
      return artifact.type === "video"
        ? '<video controls src="' + url + '"></video>'
        : "![Generated image](<" + text(artifact.url).replace(/[<>\r\n]/g, "") + ">)";
    })
    .join("\n");
}

export const protocols = {
  openai_image: {
    decodeRequest: function (ctx) {
      return protocolIntent(ctx, "image");
    },
    render: function (ctx, task) {
      return {
        data: resultURLs(task.data).map(function (url) {
          return { url: url };
        }),
      };
    },
  },
  openai_video: {
    decodeRequest: function (ctx) {
      return protocolIntent(ctx, "video");
    },
    render: function (ctx, task) {
      const urls = resultURLs(task.data);
      const output = {};
      if (task.status === "SUCCESS" && urls.length) output.url = urls[0];
      if (task.status === "FAILURE") output.error = { code: "video_generation_failed", message: task.fail_reason || "Kie generation failed" };
      return output;
    },
  },
  openai_responses: {
    decodeRequest: function (ctx) {
      return protocolIntent(ctx, "responses");
    },
    renderEvents: function (ctx, task, previousState) {
      const state = { status: task.status, progress: task.progress || "0%" };
      if (task.status === "FAILURE")
        return { events: [{ type: "error", code: "task_failed", message: task.fail_reason || "Kie generation failed" }], state: state, done: true };
      if (task.status === "SUCCESS")
        return {
          events: previousState && previousState.status === "SUCCESS" ? [] : [{ type: "output", data: responseOutput(ctx) }],
          state: state,
          done: true,
        };
      if (previousState && previousState.status === state.status && previousState.progress === state.progress) return { events: [], state: state, done: false };
      return { events: [{ type: "progress", message: String(task.status || "waiting").toLowerCase() }], state: state, done: false };
    },
    renderFinal: function (ctx) {
      return {
        output: [
          {
            type: "message",
            status: "completed",
            role: "assistant",
            content: [{ type: "output_text", text: responseOutput(ctx), annotations: [], logprobs: [] }],
          },
        ],
        metadata: { vendor: "kie" },
      };
    },
  },
};
