import type { CodeTaskLanguage, LessonAuthoringDetail, QuizQuestion } from '@/types'

export type AgeGroup = 'junior' | 'middle' | 'senior'
export type LessonFormat = 'guided' | 'skills' | 'project' | 'revision'
export type PracticeFormat = 'none' | 'text' | 'code'
export type CheckMode = 'manual' | 'keywords' | 'tests'
export type QuizQuestionType = 'single' | 'multiple' | 'order' | 'match' | 'text'

export interface JudgeTestCase {
  input: string
  expected: string
  isPublic: boolean
}

export interface ChoiceOptionDraft {
  id: string
  text: string
  correct: boolean
}

export interface MatchPairDraft {
  id: string
  left: string
  right: string
}

export interface QuizQuestionDraft {
  id: string
  type: QuizQuestionType
  prompt: string
  options: ChoiceOptionDraft[]
  orderItems: string
  correctOrder: string
  pairs: MatchPairDraft[]
  acceptedAnswers: string
}

export interface LessonBuilderForm {
  title: string
  ageGroup: AgeGroup
  duration: string
  summary: string
  passingScore: string
  lessonFormat: LessonFormat
  formatNote: string
  theoryText: string
  keyPoints: string
  interactiveSteps: string
  practiceFormat: PracticeFormat
  taskTitle: string
  taskPrompt: string
  taskHints: string
  checkMode: CheckMode
  answerKeywords: string
  programmingLanguage: CodeTaskLanguage
  starterCode: string
  timeLimitMs: string
  memoryLimitMb: string
  judgeTests: JudgeTestCase[]
  quizEnabled: boolean
  quizTitle: string
  quizPassingScore: string
  quizQuestions: QuizQuestionDraft[]
}

export interface QuizPayloadQuestion {
  id: string
  type: QuizQuestionType
  prompt: string
  options?: string[]
  items?: string[]
  left?: string[]
  right?: string[]
  correct?: number[] | string[] | Record<string, string>
}

export interface LessonBuilderSubmitData {
  title: string
  summary: string
  age_group: AgeGroup
  content_format: LessonFormat
  authoring_metadata: {
    format_note: string
  }
  duration_minutes: number
  passing_score: number
  theory_text: string
  key_points: string
  interactive_steps: string
  practice_enabled: boolean
  task_type: 'text' | 'code'
  task_title: string
  task_prompt: string
  task_hints: string
  evaluation_mode: 'manual' | 'keywords' | 'stdin_stdout'
  answer_keywords: string
  starter_code: string
  programming_language: CodeTaskLanguage | null
  judge_tests: Array<{ label: string; input: string; expected: string; is_public: boolean }>
  time_limit_ms: number | null
  memory_limit_mb: number | null
  quiz: {
    enabled: boolean
    title: string
    passing_score: number
    questions: QuizPayloadQuestion[]
  }
}

/**
 * The update contract intentionally mirrors the create builder fields while
 * grouping practice inside `task`. Both staff APIs accept this normalized
 * shape, which keeps create and edit behavior from drifting apart.
 */
export interface LessonBuilderUpdateData {
  title: string
  summary: string
  content_format: LessonFormat
  authoring_metadata: {
    format_note: string
  }
  duration_minutes: number
  passing_score: number
  theory_text: string
  key_points: string
  interactive_steps: string
  task: {
    enabled: boolean
    task_type: 'text' | 'code'
    title: string
    prompt: string
    evaluation_mode: 'manual' | 'keywords' | 'stdin_stdout'
    language: CodeTaskLanguage | null
    keywords: string
    starter_code: string
    hints: string
    tests: Array<{ label: string; input: string; expected: string; is_public: boolean }>
    time_limit_ms: number | null
    memory_limit_mb: number | null
  }
  quiz: LessonBuilderSubmitData['quiz']
}

export interface CreatedLessonState {
  id: number
  title: string
  summary: string
  version?: number
}

export const METHODICAL_SECTIONS = [
  {
    title: 'Основа урока',
    description:
      'Определяет тему, аудиторию, длительность и минимальный результат для прохождения.',
    example:
      'Хорошо: «Переменные и условия», младшая группа, 45 минут, понятное описание результата урока.',
  },
  {
    title: 'Формат урока',
    description:
      'Помогает выбрать способ подачи: пошаговый разбор, тренировка навыка, мини-проект или повторение.',
    example:
      'Если тема новая и сложная, лучше начать с пошагового разбора и мягкого темпа.',
  },
  {
    title: 'Содержание',
    description:
      'Здесь собирается объяснение, ключевые идеи и последовательность прохождения урока.',
    example:
      'Сначала короткий жизненный пример, затем разбор по шагам и мини-итог после каждого блока.',
  },
  {
    title: 'Практика',
    description:
      'Позволяет добавить упражнение сразу в урок или вынести практику в следующее действие.',
    example:
      'Для младшей группы лучше короткое текстовое задание, для старшей группы можно предложить кодовую задачу.',
  },
  {
    title: 'Проверка',
    description:
      'Определяет, как будет проверяться ответ: вручную, по ключевым словам или тестами.',
    example:
      'Если нужен точный результат в коде, используйте автотесты. Для объяснений подходит ручная проверка.',
  },
  {
    title: 'Итоговый квиз',
    description:
      'Фиксирует итог по теме: один ответ, несколько ответов, порядок, сопоставление или короткий текст.',
    example:
      'Хорошо работает как короткий финальный контроль после теории и практики, без перегруза лишними вопросами.',
  },
] as const

export const AGE_GROUP_OPTIONS: Array<{ value: AgeGroup; label: string; hint: string }> = [
  { value: 'junior', label: 'Младшая группа', hint: 'Для новичков и первых шагов.' },
  { value: 'middle', label: 'Средняя группа', hint: 'Для тех, кто уже знает базу.' },
  { value: 'senior', label: 'Старшая группа', hint: 'Для опытных учеников и углубления.' },
]

export const LESSON_FORMAT_OPTIONS: Array<{ value: LessonFormat; label: string; description: string }> = [
  {
    value: 'guided',
    label: 'Пошаговый разбор',
    description:
      'Подходит для новой темы: короткое объяснение, пример и безопасный вход в материал.',
  },
  {
    value: 'skills',
    label: 'Тренировка навыка',
    description:
      'Акцент на повторяемый прием, несколько опорных шагов и закрепление через практику.',
  },
  {
    value: 'project',
    label: 'Мини-проект',
    description:
      'Урок ведет к ощутимому результату: истории, игре, странице или небольшому инструменту.',
  },
  {
    value: 'revision',
    label: 'Повторение и закрепление',
    description:
      'Помогает быстро повторить главное перед проверкой и снять типовые ошибки.',
  },
]

export const PRACTICE_OPTIONS: Array<{ value: PracticeFormat; label: string; description: string }> = [
  {
    value: 'none',
    label: 'Без встроенной практики',
    description:
      'Только теория и разбор. Практику можно назначить позже отдельным заданием.',
  },
  {
    value: 'text',
    label: 'Текстовое задание',
    description:
      'Подходит для объяснений, коротких ответов, рассуждений и мини-упражнений.',
  },
  {
    value: 'code',
    label: 'Кодовая практика',
    description:
      'Подходит для задач с редактором, стартовым кодом и автотестами.',
  },
]

export const CHECK_OPTIONS: Array<{ value: CheckMode; label: string; description: string }> = [
  {
    value: 'manual',
    label: 'Ручная проверка',
    description:
      'Учитель сам читает ответ, оставляет комментарий и подтверждает результат.',
  },
  {
    value: 'keywords',
    label: 'Проверка по ключевым словам',
    description:
      'Система ищет ориентиры в ответе и помогает быстро проверить теоретические задания.',
  },
  {
    value: 'tests',
    label: 'Автопроверка тестами',
    description:
      'Для кода или формализованных ответов: есть входные данные и ожидаемый результат.',
  },
]

export const QUIZ_TYPE_OPTIONS: Array<{ value: QuizQuestionType; label: string; short: string }> = [
  { value: 'single', label: 'Один ответ', short: 'Один правильный вариант из нескольких.' },
  { value: 'multiple', label: 'Несколько ответов', short: 'Можно отметить несколько верных вариантов.' },
  { value: 'order', label: 'Порядок', short: 'Нужно расставить шаги в правильной последовательности.' },
  { value: 'match', label: 'Сопоставление', short: 'Нужно соединить элементы из двух колонок.' },
  { value: 'text', label: 'Текстовый ответ', short: 'Короткий текст с одним или несколькими допустимыми ответами.' },
]

export function normalizeAgeGroup(value: string | null | undefined): AgeGroup {
  if (value === 'junior' || value === 'middle' || value === 'senior') return value
  return 'middle'
}

export function ageGroupSupportsCode(group: AgeGroup) {
  return group !== 'junior'
}

export function defaultLanguageForAgeGroup(group: AgeGroup): CodeTaskLanguage {
  return group === 'senior' ? 'javascript' : 'python'
}

export function createLocalId(prefix = 'item') {
  return `${prefix}-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`
}

export function parseLines(value: string) {
  return value
    .split('\n')
    .map(item => item.trim())
    .filter(Boolean)
}

export function createEmptyTest(): JudgeTestCase {
  return { input: '', expected: '', isPublic: false }
}

export function hasCompleteJudgeTest(tests: JudgeTestCase[]) {
  // Empty stdin is a valid and common test case: many beginner tasks only
  // write a value to stdout. The expected output is the actual required part.
  return tests.some(testCase => testCase.expected.trim())
}

export function isIntegerInRange(value: string, minimum: number, maximum: number) {
  if (!/^\d+$/.test(value.trim())) return false
  const numeric = Number(value)
  return Number.isInteger(numeric) && numeric >= minimum && numeric <= maximum
}

export function createChoiceOption(): ChoiceOptionDraft {
  return { id: createLocalId('option'), text: '', correct: false }
}

export function createMatchPair(): MatchPairDraft {
  return { id: createLocalId('pair'), left: '', right: '' }
}

export function createQuizQuestion(type: QuizQuestionType = 'single'): QuizQuestionDraft {
  return {
    id: createLocalId('question'),
    type,
    prompt: '',
    options: type === 'single' || type === 'multiple' ? [createChoiceOption(), createChoiceOption()] : [],
    orderItems: '',
    correctOrder: '',
    pairs: type === 'match' ? [createMatchPair(), createMatchPair()] : [],
    acceptedAnswers: '',
  }
}

export function questionHasContent(question: QuizQuestionDraft) {
  return Boolean(
    question.prompt.trim()
    || question.options.some(option => option.text.trim())
    || question.orderItems.trim()
    || question.correctOrder.trim()
    || question.pairs.some(pair => pair.left.trim() || pair.right.trim())
    || question.acceptedAnswers.trim(),
  )
}

export function createInitialLessonBuilderForm(ageGroup: AgeGroup = 'junior'): LessonBuilderForm {
  return {
    title: '',
    ageGroup,
    duration: '45',
    summary: '',
    passingScore: '70',
    lessonFormat: 'guided',
    formatNote: '',
    theoryText: '',
    keyPoints: '',
    interactiveSteps: '',
    practiceFormat: 'text',
    taskTitle: '',
    taskPrompt: '',
    taskHints: '',
    checkMode: 'manual',
    answerKeywords: '',
    programmingLanguage: defaultLanguageForAgeGroup(ageGroup),
    starterCode: '',
    timeLimitMs: '2000',
    memoryLimitMb: '128',
    judgeTests: [createEmptyTest()],
    quizEnabled: false,
    quizTitle: '',
    quizPassingScore: '70',
    quizQuestions: [],
  }
}

function asLessonFormat(value: string | null | undefined): LessonFormat {
  return value === 'guided' || value === 'skills' || value === 'project' || value === 'revision'
    ? value
    : 'guided'
}

function asQuizQuestionType(value: string | null | undefined): QuizQuestionType {
  return value === 'single' || value === 'multiple' || value === 'order' || value === 'match' || value === 'text'
    ? value
    : 'single'
}

function asCodeLanguage(value: string | null | undefined, ageGroup: AgeGroup): CodeTaskLanguage {
  return value === 'javascript' || value === 'python'
    ? value
    : defaultLanguageForAgeGroup(ageGroup)
}

function listBlockItems(lesson: LessonAuthoringDetail) {
  const block = lesson.theory_blocks.find(item => item.type === 'list')
  return Array.isArray(block?.items) ? block.items.filter(item => typeof item === 'string') : []
}

function theoryText(lesson: LessonAuthoringDetail) {
  return lesson.theory_blocks
    .filter(item => item.type !== 'hero' && item.type !== 'list')
    .map(item => item.text?.trim() || '')
    .filter(Boolean)
    .join('\n\n')
}

function mapQuizQuestion(question: QuizQuestion): QuizQuestionDraft {
  const type = asQuizQuestionType(question.type)
  const draft = createQuizQuestion(type)
  const correctValues = Array.isArray(question.correct) ? question.correct : []

  if (type === 'single' || type === 'multiple') {
    const correctIndexes = new Set(
      correctValues
        .map(value => typeof value === 'number' ? value : Number(value))
        .filter(value => Number.isInteger(value) && value >= 0),
    )
    return {
      ...draft,
      id: question.id || draft.id,
      prompt: question.prompt || '',
      options: (question.options || []).map((text, index) => ({
        id: createLocalId('option'),
        text,
        correct: correctIndexes.has(index),
      })),
    }
  }

  if (type === 'order') {
    return {
      ...draft,
      id: question.id || draft.id,
      prompt: question.prompt || '',
      orderItems: (question.items || []).join('\n'),
      correctOrder: correctValues.map(value => String(value)).join('\n'),
    }
  }

  if (type === 'match') {
    const correct = !Array.isArray(question.correct) && question.correct && typeof question.correct === 'object'
      ? question.correct
      : {}
    const left = question.left || []
    const right = question.right || []
    const pairs = left.map((value, index) => ({
      id: createLocalId('pair'),
      left: value,
      right: correct[value] || right[index] || '',
    }))
    return {
      ...draft,
      id: question.id || draft.id,
      prompt: question.prompt || '',
      pairs: pairs.length ? pairs : draft.pairs,
    }
  }

  return {
    ...draft,
    id: question.id || draft.id,
    prompt: question.prompt || '',
    acceptedAnswers: correctValues.map(value => String(value)).join('\n'),
  }
}

function persistedDraftForm(lesson: LessonAuthoringDetail): Partial<LessonBuilderForm> | null {
  const form = lesson.draft_payload?.form
  return form && typeof form === 'object' ? form as Partial<LessonBuilderForm> : null
}

function asPracticeFormat(value: unknown): PracticeFormat {
  return value === 'none' || value === 'text' || value === 'code' ? value : 'text'
}

function asCheckMode(value: unknown): CheckMode {
  return value === 'manual' || value === 'keywords' || value === 'tests' ? value : 'manual'
}

/** Converts the staff authoring response back into the shared builder form. */
export function lessonAuthoringToForm(lesson: LessonAuthoringDetail): LessonBuilderForm {
  const ageGroup = normalizeAgeGroup(lesson.module?.age_group)
  const form = createInitialLessonBuilderForm(ageGroup)
  const task = lesson.tasks[0]
  const validation = task?.validation
  const taskIsCode = task?.task_type === 'code' || validation?.evaluation_mode === 'stdin_stdout'
  const practiceFormat: PracticeFormat = task
    ? taskIsCode
      ? 'code'
      : 'text'
    : 'none'
  const checkMode: CheckMode = taskIsCode
    ? 'tests'
    : validation?.evaluation_mode === 'keywords'
      ? 'keywords'
      : 'manual'
  const quiz = lesson.quizzes[0]

  const derived: LessonBuilderForm = {
    ...form,
    title: lesson.title || '',
    ageGroup,
    duration: String(lesson.duration_minutes || form.duration),
    summary: lesson.summary || '',
    passingScore: String(lesson.passing_score ?? form.passingScore),
    lessonFormat: asLessonFormat(lesson.content_format),
    formatNote: lesson.authoring_metadata?.format_note || lesson.format_note || '',
    theoryText: theoryText(lesson),
    keyPoints: listBlockItems(lesson).join('\n'),
    interactiveSteps: lesson.interactive_steps
      .map(step => step.text?.trim() || '')
      .filter(Boolean)
      .join('\n'),
    practiceFormat,
    taskTitle: task?.title || '',
    taskPrompt: task?.prompt || '',
    taskHints: (task?.hints || []).join('\n'),
    checkMode,
    answerKeywords: (validation?.keywords || []).join('\n'),
    programmingLanguage: asCodeLanguage(validation?.language, ageGroup),
    starterCode: task?.starter_code || '',
    timeLimitMs: String(validation?.time_limit_ms || form.timeLimitMs),
    memoryLimitMb: String(validation?.memory_limit_mb || form.memoryLimitMb),
    judgeTests: (validation?.tests || []).map(test => ({
      input: test.input || '',
      expected: test.expected || '',
      isPublic: Boolean(test.is_public),
    })).length
      ? (validation?.tests || []).map(test => ({
          input: test.input || '',
          expected: test.expected || '',
          isPublic: Boolean(test.is_public),
        }))
      : form.judgeTests,
    quizEnabled: Boolean(quiz),
    quizTitle: quiz?.title || '',
    quizPassingScore: String(quiz?.passing_score ?? form.quizPassingScore),
    quizQuestions: (quiz?.questions || []).map(mapQuizQuestion),
  }

  const draft = persistedDraftForm(lesson)
  if (!draft) return derived

  // An incomplete draft needs to preserve values that do not yet have a
  // canonical lesson representation (for example a half-written quiz). Keep
  // the class/module age group authoritative even when the browser payload is
  // old, then use the stored form for the remaining authoring fields.
  return {
    ...derived,
    ...draft,
    ageGroup,
    lessonFormat: asLessonFormat(draft.lessonFormat),
    practiceFormat: asPracticeFormat(draft.practiceFormat),
    checkMode: asCheckMode(draft.checkMode),
    programmingLanguage: asCodeLanguage(draft.programmingLanguage, ageGroup),
    judgeTests: Array.isArray(draft.judgeTests) ? draft.judgeTests : derived.judgeTests,
    quizQuestions: Array.isArray(draft.quizQuestions) ? draft.quizQuestions : derived.quizQuestions,
  }
}

export function lessonAuthoringDraftStep(lesson: LessonAuthoringDetail): number {
  const value = lesson.draft_payload?.current_step
  return typeof value === 'number' && Number.isInteger(value) && value >= 0 ? value : 0
}

export function foundationComplete(form: LessonBuilderForm) {
  return Boolean(
    form.title.trim()
    && isIntegerInRange(form.duration, 1, 480)
    && form.summary.trim()
    && isIntegerInRange(form.passingScore, 0, 100),
  )
}

export function formatComplete(form: LessonBuilderForm) {
  return Boolean(form.lessonFormat)
}

export function contentComplete(form: LessonBuilderForm) {
  return Boolean(
    form.theoryText.trim()
    && parseLines(form.keyPoints).length >= 2
    && parseLines(form.interactiveSteps).length >= 2,
  )
}

export function practiceComplete(form: LessonBuilderForm) {
  if (form.practiceFormat === 'none') return true
  if (!form.taskTitle.trim() || !form.taskPrompt.trim()) return false
  if (form.practiceFormat === 'text') return true
  return Boolean(form.programmingLanguage && form.starterCode.trim())
}

export function checkComplete(form: LessonBuilderForm) {
  if (form.practiceFormat === 'none') return true
  if (form.practiceFormat === 'code' && form.checkMode !== 'tests') return false
  if (form.checkMode === 'manual') return true
  if (form.checkMode === 'keywords') return Boolean(form.answerKeywords.trim())
  return hasCompleteJudgeTest(form.judgeTests)
}

export function buildQuizPayload(form: LessonBuilderForm): { error: string; questions: QuizPayloadQuestion[] } {
  if (!form.quizEnabled) {
    return { error: '', questions: [] }
  }

  const questions: QuizPayloadQuestion[] = []

  for (const [index, question] of form.quizQuestions.entries()) {
    if (!questionHasContent(question)) continue

    const prompt = question.prompt.trim()
    const questionNumber = index + 1

    if (!prompt) {
      return { error: `Заполните формулировку вопроса №${questionNumber}.`, questions: [] }
    }

    if (question.type === 'single' || question.type === 'multiple') {
      const options = question.options
        .map(option => ({ text: option.text.trim(), correct: option.correct }))
        .filter(option => option.text)

      if (options.length < 2) {
        return { error: `В вопросе №${questionNumber} нужно минимум два варианта ответа.`, questions: [] }
      }

      const correct = options
        .map((option, optionIndex) => option.correct ? optionIndex : -1)
        .filter(value => value >= 0)

      if (question.type === 'single' && correct.length !== 1) {
        return { error: `Для вопроса №${questionNumber} выберите ровно один правильный вариант.`, questions: [] }
      }

      if (question.type === 'multiple' && correct.length === 0) {
        return { error: `Для вопроса №${questionNumber} отметьте хотя бы один правильный вариант.`, questions: [] }
      }

      questions.push({
        id: question.id,
        type: question.type,
        prompt,
        options: options.map(option => option.text),
        correct,
      })
      continue
    }

    if (question.type === 'order') {
      const items = parseLines(question.orderItems)
      const correct = parseLines(question.correctOrder)

      if (items.length < 2) {
        return { error: `В вопросе №${questionNumber} добавьте минимум два шага.`, questions: [] }
      }

      if (correct.length !== items.length || [...correct].sort().join('|') !== [...items].sort().join('|')) {
        return {
          error: `Для вопроса №${questionNumber} правильный порядок должен содержать те же пункты, что и список шагов.`,
          questions: [],
        }
      }

      questions.push({ id: question.id, type: question.type, prompt, items, correct })
      continue
    }

    if (question.type === 'match') {
      const pairs = question.pairs
        .map(pair => ({ left: pair.left.trim(), right: pair.right.trim() }))
        .filter(pair => pair.left && pair.right)

      if (pairs.length < 2) {
        return { error: `В вопросе №${questionNumber} добавьте минимум две пары для сопоставления.`, questions: [] }
      }

      const uniqueLeft = new Set(pairs.map(pair => pair.left))
      const uniqueRight = new Set(pairs.map(pair => pair.right))

      if (uniqueLeft.size !== pairs.length) {
        return { error: `В вопросе №${questionNumber} значения слева должны быть уникальными.`, questions: [] }
      }

      if (uniqueRight.size < 2) {
        return { error: `В вопросе №${questionNumber} нужно минимум два разных значения справа.`, questions: [] }
      }

      const right: string[] = []
      const correct: Record<string, string> = {}
      for (const pair of pairs) {
        correct[pair.left] = pair.right
        if (!right.includes(pair.right)) {
          right.push(pair.right)
        }
      }

      questions.push({
        id: question.id,
        type: question.type,
        prompt,
        left: pairs.map(pair => pair.left),
        right,
        correct,
      })
      continue
    }

    const correct = parseLines(question.acceptedAnswers)
    if (!correct.length) {
      return { error: `Для вопроса №${questionNumber} добавьте хотя бы один допустимый ответ.`, questions: [] }
    }

    questions.push({ id: question.id, type: question.type, prompt, correct })
  }

  return { error: '', questions }
}

export function quizComplete(form: LessonBuilderForm, enabled: boolean) {
  if (!enabled || !form.quizEnabled) return true
  const quizPayload = buildQuizPayload(form)
  return !quizPayload.error && quizPayload.questions.length > 0
}

export function buildLessonSubmitData(form: LessonBuilderForm): LessonBuilderSubmitData {
  const judgeTests = form.checkMode === 'tests'
    ? form.judgeTests
      .filter(item => item.expected.trim())
      .map((item, index) => ({
        label: `Тест ${index + 1}`,
        input: item.input,
        expected: item.expected,
        is_public: item.isPublic,
      }))
    : []
  const quizPayload = buildQuizPayload(form)
  const practiceEnabled = form.practiceFormat !== 'none'
  const taskType = form.practiceFormat === 'code' ? 'code' : 'text'
  const evaluationMode: LessonBuilderSubmitData['evaluation_mode'] = !practiceEnabled
    ? 'manual'
    : form.practiceFormat === 'code'
      ? 'stdin_stdout'
      : form.checkMode === 'keywords'
        ? 'keywords'
        : 'manual'

  return {
    title: form.title.trim(),
    summary: form.summary.trim(),
    age_group: form.ageGroup,
    content_format: form.lessonFormat,
    authoring_metadata: {
      format_note: form.formatNote.trim(),
    },
    duration_minutes: Number(form.duration),
    passing_score: Number(form.passingScore),
    theory_text: form.theoryText,
    key_points: form.keyPoints,
    interactive_steps: form.interactiveSteps,
    practice_enabled: practiceEnabled,
    task_type: taskType,
    task_title: practiceEnabled ? form.taskTitle.trim() : '',
    task_prompt: practiceEnabled ? form.taskPrompt.trim() : '',
    task_hints: practiceEnabled ? form.taskHints : '',
    evaluation_mode: evaluationMode,
    answer_keywords: practiceEnabled && form.checkMode === 'keywords' ? form.answerKeywords : '',
    starter_code: form.practiceFormat === 'code' ? form.starterCode : '',
    programming_language: form.practiceFormat === 'code' ? form.programmingLanguage : null,
    judge_tests: judgeTests,
    time_limit_ms: form.checkMode === 'tests' ? Number(form.timeLimitMs || 2000) : null,
    memory_limit_mb: form.checkMode === 'tests' ? Number(form.memoryLimitMb || 128) : null,
    quiz: {
      enabled: form.quizEnabled,
      title: form.quizTitle.trim(),
      passing_score: Number(form.quizPassingScore || 70),
      questions: quizPayload.questions,
    },
  }
}

export function buildLessonUpdateData(
  source: LessonBuilderForm | LessonBuilderSubmitData,
): LessonBuilderUpdateData {
  const lesson = 'lessonFormat' in source ? buildLessonSubmitData(source) : source

  return {
    title: lesson.title,
    summary: lesson.summary,
    content_format: lesson.content_format,
    authoring_metadata: lesson.authoring_metadata,
    duration_minutes: lesson.duration_minutes,
    passing_score: lesson.passing_score,
    theory_text: lesson.theory_text,
    key_points: lesson.key_points,
    interactive_steps: lesson.interactive_steps,
    task: {
      enabled: lesson.practice_enabled,
      task_type: lesson.task_type,
      title: lesson.task_title,
      prompt: lesson.task_prompt,
      evaluation_mode: lesson.evaluation_mode,
      language: lesson.programming_language,
      keywords: lesson.answer_keywords,
      starter_code: lesson.starter_code,
      hints: lesson.task_hints,
      tests: lesson.judge_tests,
      time_limit_ms: lesson.time_limit_ms,
      memory_limit_mb: lesson.memory_limit_mb,
    },
    quiz: lesson.quiz,
  }
}
