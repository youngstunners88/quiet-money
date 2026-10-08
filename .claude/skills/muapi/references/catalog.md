# Muapi catalog digest (2026-10-08)

757 enabled models. Prices are USD per call from the public catalog; `~` means the price depends on the request, so run `python -m faceless muapi estimate <model>` for the exact figure. This is a snapshot: names and prices change, so `muapi find` and `muapi inspect` read the live catalog.

## Image to Video (178 models, cheapest 12 shown)
| model | price | needs | what it is |
|---|---|---|---|
| `seedance-pro-i2v-fast` | ~$0.06 | prompt, image_url | Seedance Pro Fast is the high-speed image-to-video generation variant from ByteDance’s See |
| `vidu-q2-turbo-start-end-video` | ~$0.06 | prompt, image_url, last_image | Vidu Q2 Turbo Start–End Video creates highly detailed cinematic sequences by interpolating |
| `vidu-q2-reference` | ~$0.065 | prompt, images_list | Vidu Q2 Reference Video generates breathtaking cinematic clips from text prompts guided by |
| `runway-act-two-i2v` | ~$0.07 | image_url, reference_video_url | Upload a single character image and a driving video — the model transfers facial expressio |
| `pixverse-v5.5-i2v` | ~$0.1 | prompt, images_list | PixVerse v5.5 I2V transforms a single image into a dynamic cinematic video clip. It adds s |
| `seedance-lite-i2v` | ~$0.1 | prompt, image_url | Seedance Lite I2V version animates static images into short videos quickly, focusing on ba |
| `seedance-lite-reference-video` | ~$0.1 | prompt, images_list | Seedance Lite's Reference-to-Video feature allows you to supply up to 4 images as referenc |
| `wan2.1-reference-video` | ~$0.1 | prompt, images_list | WAN 2.1 is an advanced AI model that transforms one or more reference images into a cohere |
| `wan2.7-image-to-video` | ~$0.1 | prompt, image_url | Alibaba WAN 2.7 converts images into videos with optional audio. |
| `wan2.7-reference-to-video` | ~$0.1 | prompt | Alibaba WAN 2.7 Reference-to-Video. Reference characters/props to generate new shots. |
| `ltx-2.3-image-to-video` | ~$0.104 | prompt, image_url | LTX-2.3 Image-to-Video animates a single image into a coherent cinematic clip. It preserve |
| `minimax-h3-max-turbo-image-to-video` | ~$0.13 | prompt | MiniMax H3 Max Turbo Image to Video is a faster, lower-cost H3 Max mode that animates a so |

## Text to Text (150 models, cheapest 12 shown)
| model | price | needs | what it is |
|---|---|---|---|
| `gpt-6-luna` | ~$1e-06 | prompt | GPT 6 Luna is designed for fast, high-volume text generation and focused reasoning. Offici |
| `gpt-6-sol` | ~$1e-06 | prompt | GPT 6 Sol is designed for advanced coding, reasoning, and agent workflows. Official token  |
| `gemini-2-5-flash` | ~$5e-05 | prompt | Gemini 2.5 Flash is Google's high-speed multimodal language model, optimized for rapid tex |
| `gpt-5-nano` | ~$5e-05 | prompt | GPT-5 Nano is a lightweight, high-speed language model from the GPT-5 family designed for  |
| `claude-haiku-4-5` | ~$0.0001 | prompt | Claude Haiku 4.5 is Anthropic's fastest and most cost-effective model, designed for high-f |
| `deepseek-v4-1-flash` | ~$0.0001 | prompt | DeepSeek V4.1 Flash is a multimodal reasoning model with a 1M-token context window, image  |
| `deepseek-v4-flash` | ~$0.0001 | prompt | DeepSeek V4 Flash is an ultra-fast multimodal reasoning model optimized for low-latency te |
| `gemini-3-5-flash` | ~$0.0001 | prompt | Gemini 3.5 Flash is a high-speed, multimodal language model built for real-time text gener |
| `gemini-3-5-flash-openai` | ~$0.0001 | prompt | Gemini 3.5 Flash (OpenAI-compatible) is a high-speed, multimodal language model built for  |
| `gemini-3-6-flash` | ~$0.0001 | prompt | Gemini 3.6 Flash is a high-speed, multimodal language model built for real-time text gener |
| `gemini-3-6-flash-openai` | ~$0.0001 | prompt | Gemini 3.6 Flash (OpenAI-compatible) is a high-speed, multimodal language model built for  |
| `gemini-3-7-flash` | ~$0.0001 | prompt | Gemini 3.7 Flash is a high-speed, multimodal language model built for real-time text gener |

## Text to Video (108 models, cheapest 12 shown)
| model | price | needs | what it is |
|---|---|---|---|
| `wan2.2-5b-fast-t2v` | ~$0.016 | prompt | Wan 2.2 Fast is a lightweight, high-speed version of the Wan 2.2 model, optimized for quic |
| `grok-imagine-extend` | ~$0.05 | request_id, prompt | Grok Imagine Extend lets you continue and expand existing Grok Imagine video generations s |
| `hunyuan-fast-text-to-video` | ~$0.05 | prompt | Hunyuan Fast T2V provides accelerated video generation from text prompts with slightly red |
| `seedance-pro-t2v-fast` | ~$0.06 | prompt | Seedance Pro Fast is ByteDance’s advanced text-to-video model that turns natural-language  |
| `runway-text-to-video` | ~$0.09 | prompt | Generate short, high-quality videos from plain text prompts. RunwayML’s text-to-video mode |
| `pixverse-v5.5-t2v` | ~$0.1 | prompt | PixVerse v5.5 T2V generates cinematic short videos directly from text. It excels at styliz |
| `seedance-lite-t2v` | ~$0.1 | prompt | Seedance Lite T2V offers quick video generation from text with decent visual quality and m |
| `wan2.7-text-to-video` | ~$0.1 | prompt | Alibaba WAN 2.7 Text-to-Video turns plain prompts into coherent, cinematic clips. |
| `ltx-2.3-text-to-video` | ~$0.104 | prompt | LTX-2.3 Text-to-Video generates cinematic video clips directly from text prompts. Built on |
| `minimax-h3-max-turbo-text-to-video` | ~$0.13 | prompt | MiniMax H3 Max Turbo Text to Video is a faster, lower-cost H3 Max mode that creates video  |
| `vidu-q2-turbo-text-to-video` | ~$0.13 | prompt | Vidu Q2 Turbo Text-to-Video is the fast, affordable Q2 tier for prompt-only generation. Us |
| `grok-imagine-text-to-video` | ~$0.15 | prompt | Grok Imagine is xAI’s fast, creative text-to-video model that generates cinematic clips fr |

## Video to Video (83 models, cheapest 12 shown)
| model | price | needs | what it is |
|---|---|---|---|
| `add-video-watermark` | ~$0 | video_url, watermark_image_url | Add custom watermark to videos with adjustable position, opacity, and size. Free local pro |
| `mmaudio-v2-video-to-video` | ~$0.01 | prompt, video_url | MMAudio-v2 generates high-quality, synchronized audio from video or text inputs. Seamlessl |
| `video-background-remover` | ~$0.01 | video_url | Video Background Remover automatically removes the background from any video, producing a  |
| `remix-video` | ~$0.025 | video_url | Transform and resize your videos effortlessly with remix video tool. |
| `seedance-2-watermark-remover` | ~$0.025 | video_url | 🎉 FREE for a limited time — Remove SD 2.0 watermarks from videos using LaMa AI inpainting. |
| `ai-video-upscaler` | ~$0.03 | video_url | The AI Video Upscaler is a powerful tool designed to enhance the resolution and quality of |
| `autocrop` | ~$0.05 | video_url, start_time, end_time | Automatically crop and reframe a specific video segment to your chosen aspect ratio using  |
| `video-combiner` | ~$0.05 | videos_list | Combine multiple short video clips (5s, 10s, etc.) into a single seamless full-length vide |
| `seedance-2-video-watermark-remover-pro` | ~$0.065 | video_url | SD 2 Video Watermark Remover Pro uses the SD 2 AI model to remove watermarks, logos, and o |
| `video-watermark-remover` | ~$0.065 | video_url | The AI Video Watermark Remover is our flagship model designed to remove Sora 2 watermarks, |
| `topaz-upscale-video-precision` | ~$0.08 | video_url | Upscale a video faithfully with Topaz's precision model library (Proteus, Artemis, Iris, D |
| `topaz-video-upscale` | ~$0.08 | video_url | The AI Video Upscaler is a powerful tool designed to enhance the resolution and quality of |

## Image to Image (78 models, cheapest 12 shown)
| model | price | needs | what it is |
|---|---|---|---|
| `add-image-watermark` | ~$0 | image_url, watermark_image_url | Add custom watermark to images with adjustable position, opacity, and size. Free local pro |
| `gemini-omni-character` | ~$0 | descriptions, images_list | Generate a reusable character from a single reference image and a text description. Option |
| `flux-2-klein-4b-turbo-edit` | ~$0.0078 | prompt, images_list | Flux-2-Klein-4B Turbo Edit provides ultra-fast, instruction-based image editing. This high |
| `ai-background-remover` | ~$0.01 | image_url | Instantly remove image backgrounds with pixel-perfect precision. Ideal for product photos, |
| `ai-color-photo` | ~$0.01 | image_url | Automatically add lifelike colors to black-and-white images. Our AI brings history to life |
| `ai-skin-enhancer` | ~$0.01 | image_url | Smooth skin, reduce blemishes, and enhance complexion with natural-looking results. Perfec |
| `flux-redux` | ~$0.01 | prompt, image_url | Flux Redux is a transformation model that reimagines or enhances your input images while p |
| `minimax-image-01-subject-reference` | ~$0.01 | prompt, image_url | Minimax’s I2I “Subject Reference” model enables you to transform images while preserving t |
| `portrait-stylist` | ~$0.01 | image_url, name | Professional AI portrait styles including hair, makeup, style, and fashion transformations |
| `flux-2-klein-9b-turbo-edit` | ~$0.0104 | prompt, images_list | Flux-2-Klein-9B Turbo Edit offers high-quality, ultra-fast image editing with superior det |
| `flux-2-klein-4b-edit` | ~$0.0156 | prompt, images_list | Flux-2-Klein-4B Edit applies lightweight, instruction-based edits to an existing image. It |
| `ai-image-face-swap` | ~$0.02 | image_url, swap_url | Advanced facial recognition and blending algorithms enable precise face swaps while preser |

## Text to Image (71 models, cheapest 12 shown)
| model | price | needs | what it is |
|---|---|---|---|
| `flux-schnell` | ~$0.003 | prompt | Flux Schnell is a lightning-fast image generation model designed for rapid iterations. It  |
| `sdxl-image` | ~$0.004 | prompt | SDXL is a high-quality, large Stable Diffusion model for creating photorealistic and styli |
| `z-image-p` | ~$0.004 | prompt | Z-Image P is based on the Qubico/z-image text-to-image model. |
| `flux-2-klein-4b-turbo` | ~$0.0052 | prompt | Flux-2-Klein-4B Turbo is an ultra-fast, high-efficiency text-to-image model. It is a disti |
| `flux-2-klein-9b-turbo` | ~$0.0065 | prompt | Flux-2-Klein-9B Turbo is a high-performance, mid-size text-to-image model. This distilled  |
| `z-image-turbo` | ~$0.007 | prompt | Z-Image Turbo is a high-speed text-to-image model optimized for fast creative generation.  |
| `hidream-i1-fast` | ~$0.008 | prompt | Optimized for speed, this variant generates images in just a few steps. Ideal for previews |
| `flux-2-klein-4b` | ~$0.0104 | prompt | Flux-2-Klein-4B is a lightweight, fast text-to-image model optimized for clear subject ren |
| `flux-2-klein-9b` | ~$0.013 | prompt | Flux-2-Klein-9B is a mid-size text-to-image model that balances detail quality and generat |
| `z-image-base` | ~$0.013 | prompt | Z-Image Base is a general-purpose text-to-image model designed for reliable, high-quality  |
| `flux-2-dev` | ~$0.015 | prompt | Flux 2 Dev is a powerful text-to-image diffusion model designed for high-quality, fast, an |
| `flux-dev` | ~$0.015 | prompt | Generate stunning visuals from simple text prompts. Flux Dev transforms your ideas into hi |

## Text to Audio (20 models, cheapest 12 shown)
| model | price | needs | what it is |
|---|---|---|---|
| `suno-voice-clone` | ~$0 | audio_url | Clone your singing voice in two takes for use with Suno music generation. Submit a 10-seco |
| `gemini-3-8-flash-lite-tts` | ~$0.01 | speakers, dialogue_turns | Gemini 3.8 Flash Lite TTS is Google's high-throughput, low-latency, cost-efficient text-to |
| `mmaudio-v2-text-to-audio` | ~$0.01 | prompt | Convert text into natural-sounding speech using mmAudio-v2. Ideal for voiceovers, virtual  |
| `suno-convert-to-wav` | ~$0.01 | task_id, audio_id | Converts an existing Suno-generated music track to high-quality, uncompressed WAV format f |
| `gemini-3-8-flash-tts` | ~$0.015 | speakers, dialogue_turns | Gemini 3.8 Flash TTS turns written dialogue into expressive, natural multi-speaker speech  |
| `suno-generate-sounds` | ~$0.02 | prompt | Generate sound effects using Suno chirp-crow model. |
| `gemini-2-5-pro-tts` | ~$0.035 | speakers, dialogue_turns | Gemini 2.5 Pro TTS is Google's premium text-to-speech model for studio-quality, high-fidel |
| `gemini-3-1-flash-tts` | ~$0.035 | speakers, dialogue_turns | Gemini 3.1 Flash TTS turns written dialogue into expressive, natural multi-speaker speech  |
| `elevenlabs-tts-turbo-2-5` | ~$0.05 | prompt | Convert text to natural-sounding speech using the ElevenLabs TTS Turbo 2.5 model, with adj |
| `suno-add-instrumental` | ~$0.09 | title, tags, audio_url | Add instrumental backing to acapella audio. |
| `suno-add-vocals` | ~$0.09 | prompt, title, style, audio_url | Add vocals to an instrumental track. |
| `suno-create-music` | ~$0.09 | style | Suno generate music that turns text prompts into full songs — complete with vocals, lyrics |

## Lora Support (17 models, cheapest 12 shown)
| model | price | needs | what it is |
|---|---|---|---|
| `z-image-base-text-to-image-lora` | ~$0.01 | prompt | Z-Image-Base LoRA (6B) text-to-image and image-to-image generation model with external LoR |
| `z-image-turbo-image-to-image-lora` | ~$0.01 | prompt, image_url | Z-Image-Turbo Image-to-Image LoRA transforms reference images with custom LoRA styles in s |
| `z-image-turbo-text-to-image-lora` | ~$0.01 | prompt | Z-Image-Turbo LoRA (6B) enables ultra-fast text-to-image generation with external LoRA sup |
| `krea-v2-turbo-lora` | ~$0.015 | prompt | Krea 2 Turbo LoRA runs custom LoRA adapters and generates personalized images natively at  |
| `flux-2-klein-4b-text-to-image-lora` | ~$0.02 | prompt | Flux-2-Klein-4B Text-to-Image with LoRA pairs the lightweight Klein 4B model with custom L |
| `qwen-image-text-to-image-2512-lora` | ~$0.02 | prompt | Qwen-Image Text-to-Image 2512 LoRA pairs the 20B MMDiT next-generation text-to-image model |
| `qwen-image-text-to-image-lora` | ~$0.02 | prompt | Qwen-Image Text-to-Image LoRA pairs the 20B MMDiT next-generation text-to-image model with |
| `flux-1-dev-style-lora-inference` | ~$0.025 | prompt, lora_url | Run FLUX.1 [dev] text-to-image inference with your trained LoRA applied. Pass the `air` id |
| `flux-2-klein-4b-edit-lora` | ~$0.025 | prompt, images_list | Flux-2-Klein-4B Edit with LoRA performs instruction-based image edits while applying custo |
| `flux-2-klein-9b-text-to-image-lora` | ~$0.025 | prompt | Flux-2-Klein-9B Text-to-Image with LoRA combines the higher-fidelity Klein 9B base with cu |
| `flux-2-klein-9b-edit-lora` | ~$0.03 | prompt, images_list | Flux-2-Klein-9B Edit with LoRA delivers higher-fidelity, instruction-based edits combined  |
| `qwen-image-edit-2511-lora` | ~$0.04 | prompt, images_list | Qwen Image Edit 2511 LoRA is an enhanced version with custom LoRA support for personalized |

## other (16 models, cheapest 12 shown)
| model | price | needs | what it is |
|---|---|---|---|
| `gemini-omni-audio` | ~$0 | audio_id, name | Create a named voice profile with custom timbre, style, and emotion. The returned voice ID |
| `moderate-image` | ~$0.01 | image_url | Detect unsafe or policy-violating content in any image. Supply an image URL (and optional  |
| `youtube-download` | ~$0.01 | video_url | Download videos from YouTube in your chosen resolution or audio format. |
| `youtube-publish` | ~$0.01 | account_id, media_url, title | Upload and publish a video to a connected YouTube account. |
| `youtube-set-thumbnail` | ~$0.01 | account_id, video_id, thumbnail_url | Set or replace the thumbnail image of a video on a connected YouTube account. |
| `youtube-update-metadata` | ~$0.01 | account_id, video_id | Update the title, description, tags, category, privacy, or made-for-kids status of a video |
| `openai-whisper` | ~$0.012 | audio_url | Whisper turns spoken audio into accurate written text. Upload an audio file URL and receiv |
| `facebook-publish` | ~$0.02 | account_id, media_url | Publish a video or image to a connected Facebook Page. |
| `instagram-publish` | ~$0.02 | account_id, media_url | Publish a video or image to a connected Instagram Business account. |
| `linkedin-publish` | ~$0.02 | account_id, media_url | Publish a video or image to a connected LinkedIn profile or page. |
| `moderate-video` | ~$0.02 | video_url | Scan a video for unsafe or policy-violating content. Supports MP4, MOV, and WebM URLs and  |
| `ocr-recognize-text` | ~$0.02 | image_url | Detect and extract text fragments and their positions from an image using local OCR. |

## Audio to Video (13 models, cheapest 12 shown)
| model | price | needs | what it is |
|---|---|---|---|
| `creatify-lipsync` | ~$0.04 | audio_url, video_url | Realistic lipsync video - optimized for speed, quality, and consistency. |
| `latent-sync` | ~$0.04 | audio_url, video_url | LatentSync is a video-to-video model that generates lip sync animations from audio using a |
| `sync-lipsync` | ~$0.04 | audio_url, video_url | Generate realistic lipsync animations from audio using advanced algorithms for high-qualit |
| `veed-lipsync` | ~$0.04 | audio_url, video_url | Generate realistic lipsync from any audio using VEED's latest model |
| `infinitetalk-image-to-video` | ~$0.2 | image_url, audio_url | InfiniteTalk Image-to-Video brings still portraits and character photos to life by generat |
| `ltx-2-19b-lipsync` | ~$0.2 | audio_url | LTX-2-19B LipSync generates a realistic talking video by synchronizing a person’s mouth mo |
| `wan2.2-speech-to-video` | ~$0.2 | image_url, audio_url | WAN2.2 Speech-to-Video transforms a static image into a talking video by synchronizing lip |
| `omnihuman-1-5` | ~$0.25 | image_url, audio_url | Generate realistic talking head video from portrait image and audio using OmniHuman 1.5. |
| `ltx-2.3-lipsync` | ~$0.26 | audio_url | LTX-2.3 LipSync generates a realistic talking video by synchronizing mouth movements to an |
| `kling-v1-avatar-standard` | ~$0.35 | image_url, audio_url | Kling AI Avatar Standard creates talking avatar videos from a single image + audio input.  |
| `kling-v2-avatar-standard` | ~$0.35 | image_url, audio_url | AI-Avatar v2 Standard generates a talking-avatar video from a reference image and an audio |
| `kling-v1-avatar-pro` | ~$0.65 | image_url, audio_url | Kling AI Avatar Pro is the premium tier for making high-quality talking avatars. You uploa |

## Training (13 models, cheapest 12 shown)
| model | price | needs | what it is |
|---|---|---|---|
| `sdxl-lora` | ~$0.002 | prompt | The SDXL LoRA image model enhances Stable Diffusion XL with specialized fine-tuning, letti |
| `flux-dev-lora` | ~$0.015 | prompt, model_id | Enables text-to-image generation using custom LoRA models. Generate consistent characters, |
| `flux-1-dev-style-lora-trainer` | ~$0.25 | dataset | Produce style-focused LoRA adapters on top of the FLUX.1 [dev] architecture. Upload a ZIP  |
| `wan2.1-lora-i2v` | ~$0.3 | prompt, image_url | Bring still images to life using WAN 2.1 LoRA I2V, which supports custom LoRA fine-tunes f |
| `wan2.1-lora-t2v` | ~$0.3 | prompt | WAN 2.1 LoRA T2V enables users to generate videos from text prompts with custom-trained Lo |
| `seedance-2-omni-reference-train` | ~$0.5 | image_url, character_name | Train a reusable character from a reference photo. Once complete, reference the character  |
| `qwen-image-2512-lora-trainer` | ~$2 | data | Train custom Qwen-Image-2512 LoRA models 10x faster with style, character, and object trai |
| `qwen-image-lora-trainer` | ~$2 | data | Train custom Qwen-Image LoRA models 10x faster. Fine-tune styles, characters, or object co |
| `z-image-base-lora-trainer` | ~$2.5 | data | Train custom Z-Image Base LoRA models from your dataset with zip uploads, auto-tuned defau |
| `z-image-lora-trainer` | ~$2.5 | data | Train custom image LoRA models from your dataset with zip uploads, auto-tuned defaults, an |
| `flux-lora-trainer` | ~$3.2 | images_data_url | Train a custom Flux LoRA from your own images. Upload a .zip of 10-50 photos (and optional |
| `flux-2-klein-9b-style-lora-trainer` | ~$4 | dataset | Produce style-focused LoRA adapters on top of the FLUX.2 [klein] 9B architecture. Upload a |

## Image to 3D (7 models, cheapest 7 shown)
| model | price | needs | what it is |
|---|---|---|---|
| `tripo3d-h31-multiview-to-3d` | ~$0.2 | images_list | Reconstruct a 3D model from 2-4 reference images taken from different angles. Multi-view c |
| `tripo3d-h31-image-to-3d` | ~$0.3 | image_url | Convert a single image into a highly detailed 3D model with selectable texture quality and |
| `meshy-6-image-to-3d` | ~$0.5 | image_url | Generate a clean 3D mesh from a single reference image. Output is a textured .glb plus FBX |
| `meshy-6-multi-image-to-3d` | ~$0.5 | images_list | Reconstruct a 3D mesh from 1-4 reference images. Multi-view inputs produce more accurate g |
| `tripo3d-p1-image-to-3d` | ~$0.5 | image_url | Turn a single reference image into a textured 3D mesh. Output is a watertight .glb ready f |
| `meshy-v7-image-to-3d` | ~$1.716 | image_url | Generate a clean, textured PBR 3D mesh from a single reference image using Meshy V7. Suppo |
| `meshy-v7-multi-image-to-3d` | ~$1.716 | images_list | Reconstruct a clean, textured PBR 3D model from 1 to 4 reference images of the same object |

## Text to 3D (3 models, cheapest 3 shown)
| model | price | needs | what it is |
|---|---|---|---|
| `tripo3d-h31-text-to-3d` | ~$0.2 | prompt | High-quality text-to-3D with selectable texture and geometry quality, optional PBR materia |
| `meshy-6-text-to-3d` | ~$0.5 | prompt | Generate detailed 3D models from text with configurable topology, polygon count, symmetry, |
| `tripo3d-p1-text-to-3d` | ~$0.5 | prompt | Generate textured 3D meshes directly from a text prompt. Outputs a clean .glb with optiona |
