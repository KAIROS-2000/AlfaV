'use client'

import { UserLocalTime } from '@/components/user-local-time'
import { clampPageToPagination, FiveItemPager, SERVER_PAGE_SIZE, useFiveItemWindow } from '@/components/five-item-navigator'
import { api, getApiErrorMessage } from '@/lib/api'
import { showErrorToast, showSuccessToast } from '@/lib/toast'
import {
	AssignmentItem,
	ClassJoinRequestItem,
	ClassroomItem,
	CodeTaskLanguage,
	LessonCatalogItem,
	SubmissionItem,
	TaskEvaluationMode,
	TeacherClassDetail,
	TeacherAssignmentsResponse,
	TeacherJoinRequestsResponse,
	TeacherLessonCatalogResponse,
	TeacherOverviewData,
	TeacherSubmissionsResponse,
	PaginationMeta,
} from '@/types'
import {
	CalendarClock,
	ClipboardCheck,
	Copy,
	FilePlus2,
	ListChecks,
	Search,
	Users,
} from 'lucide-react'
import Link from 'next/link'
import {
	useEffect,
	useMemo,
	useRef,
	useState,
	type FormEvent,
	type ReactNode,
} from 'react'

type AssignmentType = AssignmentItem['assignment_type']
type SubmissionFormat = AssignmentItem['submission_format']

type Difficulty = 'easy' | 'medium' | 'hard'
type LessonBlueprintKey = 'guided' | 'skills' | 'project' | 'revision'
type LessonPracticeMode = 'none' | 'text' | 'code'
type ClassRequiredField = 'name'
type JoinRequestAction = 'approve' | 'reject'
type LessonSourceFilter = 'all' | LessonCatalogItem['source']
type SubmissionReviewFilter = 'pending' | 'checked' | 'needs_revision'

interface LessonJudgeTestCase {
	input: string
	expected: string
}

interface LessonFormState {
	title: string
	summary: string
	theory_text: string
	key_points: string
	interactive_steps: string
	task_title: string
	task_prompt: string
	answer_keywords: string
	starter_code: string
	task_hints: string
	age_group: 'junior' | 'middle' | 'senior'
	duration_minutes: string
	passing_score: string
	task_xp_reward: string
	evaluation_mode: TaskEvaluationMode
	programming_language: CodeTaskLanguage
	time_limit_ms: string
	memory_limit_mb: string
	judge_tests: LessonJudgeTestCase[]
}

interface LessonBlueprint {
	label: string
	short: string
	description: string
	durationByAge: Record<'junior' | 'middle' | 'senior', string>
	passingScore: string
	taskXpReward: string
	recommendedPractice: LessonPracticeMode
	sampleTitle: Record<'junior' | 'middle' | 'senior', string>
	summary: (theme: string) => string
	theory: (theme: string) => string
	keyPoints: string
	steps: string
	taskTitle: (theme: string) => string
	taskPrompt: (theme: string) => string
	keywords: string
	hints: string
	starterCode: string
}

interface AssignmentFormState {
	title: string
	description: string
	lesson_id: string
	due_date: string
	difficulty: Difficulty
	xp_reward: string
	assignment_type: AssignmentType
	submission_format: SubmissionFormat
	learning_goal: string
	work_steps: string
	success_criteria: string
	resources: string
}

type AssignmentRequiredField =
	| 'title'
	| 'lesson_id'
	| 'due_date'
	| 'learning_goal'
	| 'resources'
	| 'work_steps'
	| 'success_criteria'
	| 'description'

interface AssignmentTemplate {
	label: string
	short: string
	title: string
	description: string
	learning_goal: string
	work_steps: string
	success_criteria: string
	resources: string
	submission_format: SubmissionFormat
}

const ASSIGNMENT_TEMPLATES: Record<AssignmentType, AssignmentTemplate> = {
	lesson_practice: {
		label: 'Практика по уроку',
		short: 'Закрепление навыка после конкретного урока.',
		title: 'Практика по уроку',
		description:
			'Закрепите ключевые навыки урока и покажите рабочий результат.',
		learning_goal: 'Применить идею урока в самостоятельном решении.',
		work_steps:
			'Прочитай задание.\nСделай решение.\nПроверь результат перед отправкой.',
		success_criteria:
			'Решение связано с темой урока.\nЕсть корректный итоговый результат.',
		resources: 'Конспект урока.\nПримеры из практики.',
		submission_format: 'mixed',
	},
	mini_project: {
		label: 'Мини-проект',
		short: 'Небольшой проект с ссылкой на результат.',
		title: 'Мини-проект',
		description:
			'Создайте небольшой проект по теме и опишите архитектуру решения.',
		learning_goal:
			'Научиться собирать задачу в цельный проект и презентовать результат.',
		work_steps:
			'Определи идею проекта.\nСобери рабочую версию.\nПодготовь короткую презентацию.',
		success_criteria:
			'Проект запускается или читается без пояснений.\nЕсть описание, как это работает.',
		resources: 'Репозиторий примеров.\nШаблоны интерфейса/кода.',
		submission_format: 'link',
	},
	quiz: {
		label: 'Квиз / тест',
		short: 'Проверка теории и логики по теме.',
		title: 'Квиз по теме',
		description:
			'Пройдите контрольный мини-тест и аргументируйте сложные ответы.',
		learning_goal: 'Проверить понимание терминов и базовой логики темы.',
		work_steps:
			'Ответь на вопросы.\nПроверь спорные пункты.\nДобавь короткие пояснения.',
		success_criteria:
			'Большинство ответов верные.\nПояснения логичные и по теме.',
		resources: 'Конспект урока.\nСловарь терминов.',
		submission_format: 'text',
	},
	reflection: {
		label: 'Рефлексия',
		short: 'Разбор результата и план улучшений.',
		title: 'Рефлексия по теме',
		description:
			'Сформулируйте, что получилось, что вызвало сложности и как улучшить результат.',
		learning_goal: 'Развить навык анализа собственной работы.',
		work_steps:
			'Опиши, что сделал.\nВыдели сложные моменты.\nПредложи следующий шаг.',
		success_criteria: 'Есть честный разбор.\nЕсть конкретный план улучшений.',
		resources: 'Личный конспект.\nОбратная связь учителя.',
		submission_format: 'text',
	},
}

const ASSIGNMENT_TYPES: AssignmentType[] = [
	'lesson_practice',
	'mini_project',
	'quiz',
	'reflection',
]

const SUBMISSION_FORMAT_OPTIONS: Array<{
	value: SubmissionFormat
	label: string
}> = [
	{ value: 'text', label: 'Текст' },
	{ value: 'code', label: 'Код' },
	{ value: 'link', label: 'Ссылка' },
	{ value: 'mixed', label: 'Свободный формат' },
]

const SUBMISSION_FORMAT_LABELS: Record<SubmissionFormat, string> = {
	text: 'Текст',
	code: 'Код',
	link: 'Ссылка',
	mixed: 'Свободный формат',
}

const REVIEWED_SUBMISSION_STATUSES = new Set<SubmissionItem['status']>([
	'checked',
	'needs_revision',
])

const SUBMISSION_STATUS_LABELS: Record<SubmissionItem['status'], string> = {
	submitted: 'Отправлено',
	pending_review: 'Ожидает проверки',
	checked: 'Верно',
	needs_revision: 'Неверно',
}

const LESSON_SOURCE_FILTER_OPTIONS: Array<{
	value: LessonSourceFilter
	label: string
}> = [
	{ value: 'all', label: 'Все источники' },
	{ value: 'catalog', label: 'Каталог' },
	{ value: 'teacher', label: 'Уроки учителя' },
]

const SUBMISSION_REVIEW_FILTERS: Array<{
	value: SubmissionReviewFilter
	label: string
}> = [
	{ value: 'pending', label: 'Ожидают' },
	{ value: 'checked', label: 'Проверены' },
	{ value: 'needs_revision', label: 'На доработке' },
]

const TEACHER_ZONES = [
	{ id: 'teacher-overview', label: 'Главное' },
	{ id: 'teacher-classes', label: 'Классы' },
	{ id: 'teacher-lessons', label: 'Уроки' },
	{ id: 'teacher-assignments', label: 'Задания' },
	{ id: 'teacher-review', label: 'Проверка' },
] as const

const DIFFICULTY_LABELS: Record<Difficulty, string> = {
	easy: 'Легкая',
	medium: 'Средняя',
	hard: 'Сложная',
}

function getDifficultyLabel(value: string | null | undefined) {
	if (value === 'easy' || value === 'medium' || value === 'hard') {
		return DIFFICULTY_LABELS[value]
	}
	return value || '—'
}

function practiceHeatSegmentColor(
	failureRate: number | null,
	reviewed: number,
): string {
	if (reviewed === 0) return 'rgb(226 232 240)'
	const x = Math.min(100, Math.max(0, failureRate ?? 0)) / 100
	const r = Math.round(16 + (244 - 16) * x)
	const g = Math.round(185 + (63 - 185) * x)
	const b = Math.round(129 + (94 - 129) * x)
	return `rgb(${r} ${g} ${b})`
}

const EMPTY_ASSIGNMENT_FORM: AssignmentFormState = {
	title: '',
	description: '',
	lesson_id: '',
	due_date: '',
	difficulty: 'medium',
	xp_reward: '80',
	assignment_type: 'lesson_practice',
	submission_format: ASSIGNMENT_TEMPLATES.lesson_practice.submission_format,
	learning_goal: '',
	work_steps: '',
	success_criteria: '',
	resources: '',
}

const ASSIGNMENT_REQUIRED_FIELD_LABELS: Record<
	AssignmentRequiredField,
	string
> = {
	title: 'название задания',
	lesson_id: 'урок',
	due_date: 'дедлайн',
	learning_goal: 'цель обучения',
	resources: 'материалы',
	work_steps: 'шаги выполнения',
	success_criteria: 'критерии успеха',
	description: 'описание задания',
}

const CLASS_REQUIRED_FIELD_LABELS: Record<ClassRequiredField, string> = {
	name: 'название класса',
}

function getMissingClassFields(form: {
	name: string
	description: string
}): ClassRequiredField[] {
	return form.name.trim() ? [] : ['name']
}

function getMissingAssignmentFields(
	form: AssignmentFormState,
): AssignmentRequiredField[] {
	const missing: AssignmentRequiredField[] = []

	if (!form.title.trim()) missing.push('title')
	if (!form.lesson_id.trim()) missing.push('lesson_id')
	if (!form.due_date.trim()) missing.push('due_date')
	if (!form.learning_goal.trim()) missing.push('learning_goal')
	if (!form.resources.trim()) missing.push('resources')
	if (!form.work_steps.trim()) missing.push('work_steps')
	if (!form.success_criteria.trim()) missing.push('success_criteria')
	if (!form.description.trim()) missing.push('description')

	return missing
}

function defaultProgrammingLanguage(
	ageGroup: 'junior' | 'middle' | 'senior',
): CodeTaskLanguage {
	return ageGroup === 'senior' ? 'javascript' : 'python'
}

function ageGroupSupportsCodePractice(
	ageGroup: 'junior' | 'middle' | 'senior',
) {
	return ageGroup !== 'junior'
}

function defaultEvaluationMode(
	practiceMode: LessonPracticeMode,
): TaskEvaluationMode {
	if (practiceMode === 'code') return 'stdin_stdout'
	return 'manual'
}

function createEmptyJudgeTest(): LessonJudgeTestCase {
	return { input: '', expected: '' }
}

function buildEmptyLessonForm(
	ageGroup: 'junior' | 'middle' | 'senior' = 'middle',
	practiceMode: LessonPracticeMode = 'text',
): LessonFormState {
	return {
		title: '',
		summary: '',
		theory_text: '',
		key_points: '',
		interactive_steps: '',
		task_title: '',
		task_prompt: '',
		answer_keywords: '',
		starter_code: '',
		task_hints: '',
		age_group: ageGroup,
		duration_minutes: '10',
		passing_score: '70',
		task_xp_reward: '30',
		evaluation_mode: defaultEvaluationMode(practiceMode),
		programming_language: defaultProgrammingLanguage(ageGroup),
		time_limit_ms: '2000',
		memory_limit_mb: '128',
		judge_tests: practiceMode === 'code' ? [createEmptyJudgeTest()] : [],
	}
}

const EMPTY_LESSON_FORM: LessonFormState = buildEmptyLessonForm()

const LESSON_BLUEPRINT_KEYS: LessonBlueprintKey[] = [
	'guided',
	'skills',
	'project',
	'revision',
]

const LESSON_BLUEPRINTS: Record<LessonBlueprintKey, LessonBlueprint> = {
	guided: {
		label: 'Понятно с нуля',
		short: 'Коротко, спокойно, без перегруза.',
		description:
			'Для новой темы, когда нужно быстро ввести ученика в контекст и сразу закрепить смысл.',
		durationByAge: { junior: '15', middle: '20', senior: '25' },
		passingScore: '65',
		taskXpReward: '25',
		recommendedPractice: 'text',
		sampleTitle: {
			junior: 'Как работает алгоритм',
			middle: 'Переменные и условия',
			senior: 'Функции и параметры',
		},
		summary: theme =>
			`Урок знакомит с темой «${theme}» простым языком и показывает, как применить ее на понятном примере.`,
		theory: theme =>
			`Начните с жизненного примера, где тема «${theme}» действительно нужна.\nПотом объясните основной принцип простыми словами.\nЗакончите коротким выводом: что ученик должен запомнить после урока.`,
		keyPoints:
			'Что означает тема простыми словами\nГде она встречается на практике\nКакой шаг здесь самый важный\nКакая ошибка бывает чаще всего',
		steps:
			'Покажите стартовую ситуацию\nРазберите пример по шагам\nПопросите предсказать следующий шаг\nСоберите короткий итог урока',
		taskTitle: theme => `Мини-практика: ${theme}`,
		taskPrompt: theme =>
			`Объясни тему «${theme}» своими словами и выполни короткое упражнение по образцу из урока.`,
		keywords: 'понятие, шаг, результат',
		hints:
			'Вернись к ключевым идеям урока.\nСравни решение с примером из разбора.\nПроверь, что в ответе есть понятный итог.',
		starterCode: '',
	},
	skills: {
		label: 'Навык через действие',
		short: 'Меньше теории, больше повторяемого приема.',
		description:
			'Подходит для уроков, где важнее отработать шаблон решения, чем просто узнать новый термин.',
		durationByAge: { junior: '20', middle: '30', senior: '35' },
		passingScore: '70',
		taskXpReward: '35',
		recommendedPractice: 'text',
		sampleTitle: {
			junior: 'Повторяем команды шаг за шагом',
			middle: 'Циклы на простых примерах',
			senior: 'Массивы и поиск элементов',
		},
		summary: theme =>
			`Урок по теме «${theme}» помогает довести прием до уверенного использования через разбор и самостоятельное повторение.`,
		theory: theme =>
			`Сначала сформулируйте, какой конкретный навык дает тема «${theme}».\nПотом покажите базовый шаблон действий.\nОтдельно подчеркните, как ученик быстро проверит себя.`,
		keyPoints:
			'Как выглядит базовый шаблон решения\nГде ученики ошибаются чаще всего\nКак быстро проверить себя\nКогда этот прием лучше не использовать',
		steps:
			'Соберите решение вместе с классом\nПосле каждого шага задайте вопрос «почему»\nСравните правильный и ошибочный вариант\nДайте короткое повторение по памяти',
		taskTitle: theme => `Тренировка навыка: ${theme}`,
		taskPrompt: theme =>
			`Реши самостоятельную задачу по теме «${theme}» и постарайся повторить тот же алгоритм, что был в разборе.`,
		keywords: 'алгоритм, проверка, ошибка',
		hints:
			'Сначала повтори порядок шагов из урока.\nПроверь промежуточный результат до финального ответа.\nЕсли запутался, найди шаг, на котором изменилась логика.',
		starterCode: '',
	},
	project: {
		label: 'Мини-проект',
		short: 'Урок с заметным результатом на выходе.',
		description:
			'Подходит для тем, где хочется получить артефакт: историю, игру, страницу, мини-инструмент.',
		durationByAge: { junior: '25', middle: '40', senior: '50' },
		passingScore: '75',
		taskXpReward: '60',
		recommendedPractice: 'text',
		sampleTitle: {
			junior: 'Собираем мини-историю по шагам',
			middle: 'Мини-игра с условиями',
			senior: 'Трекер задач на функциях',
		},
		summary: theme =>
			`Урок по теме «${theme}» ведет к небольшому, но законченному результату, который можно показать и объяснить.`,
		theory: theme =>
			`Покажите, какой результат ученик соберет по итогам темы «${theme}».\nРазделите объяснение на три части: идея, структура, проверка результата.\nОбязательно скажите, какой минимум уже считается успехом.`,
		keyPoints:
			'Как выглядит минимально рабочая версия\nКакие части можно собрать по очереди\nКак проверить, что каждая часть работает\nЧто можно улучшить после базовой версии',
		steps:
			'Сначала соберите каркас результата\nДобавьте одну ключевую механику\nПроверьте работоспособность на коротком сценарии\nОбсудите, что улучшить дальше',
		taskTitle: theme => `Мини-проект: ${theme}`,
		taskPrompt: theme =>
			`Собери свою рабочую версию по теме «${theme}». Важно получить результат, который можно открыть, показать или быстро объяснить.`,
		keywords: 'результат, структура, проверка',
		hints:
			'Сначала добейся минимально рабочего варианта.\nПроверяй результат после каждого крупного шага.\nОпиши, что уже работает, даже если не все готово.',
		starterCode: '// Здесь можно оставить каркас решения или базовый шаблон.\n',
	},
	revision: {
		label: 'Повторение и закрепление',
		short: 'Собрать главное перед проверкой.',
		description:
			'Для уроков, где нужно быстро повторить тему, отделить главное от второстепенного и снять типовые ошибки.',
		durationByAge: { junior: '15', middle: '20', senior: '25' },
		passingScore: '80',
		taskXpReward: '20',
		recommendedPractice: 'none',
		sampleTitle: {
			junior: 'Что мы запомнили про алгоритмы',
			middle: 'Повторение темы перед проверкой',
			senior: 'Быстрый обзор ключевых паттернов',
		},
		summary: theme =>
			`Урок помогает быстро повторить тему «${theme}», собрать главное и увидеть, где еще есть пробелы.`,
		theory: theme =>
			`Соберите в одном месте все, что нужно удержать по теме «${theme}».\nСравните близкие понятия, покажите типовые ошибки и дайте короткую памятку для самопроверки.`,
		keyPoints:
			'Какие идеи обязательно помнить\nЧем похожие понятия отличаются\nКакие ошибки чаще всего срезают результат\nПо какому чек-листу себя проверить',
		steps:
			'Попросите учеников назвать все, что они уже помнят\nСоберите общий список ключевых идей\nРазберите 2-3 типовые ошибки\nЗакончите памяткой или чек-листом',
		taskTitle: theme => `Чек-ап по теме: ${theme}`,
		taskPrompt: theme =>
			`Собери короткую памятку по теме «${theme}» и покажи на одном примере, что ты различаешь правильный и ошибочный вариант.`,
		keywords: 'чек-лист, ошибка, главное',
		hints:
			'Не пытайся записать все, только самое важное.\nСравни правильный и неправильный пример.\nПроверь, можно ли по твоему ответу быстро повторить тему.',
		starterCode: '',
	},
}

const PRACTICE_MODE_OPTIONS: Array<{
	value: LessonPracticeMode
	label: string
	short: string
}> = [
	{
		value: 'none',
		label: 'Без встроенной практики',
		short: 'Только теория и разбор',
	},
	{
		value: 'text',
		label: 'Мини-практика',
		short: 'Короткий ответ или упражнение',
	},
	{ value: 'code', label: 'Кодовая практика', short: 'Редактор и автотесты' },
]

const TEXT_EVALUATION_OPTIONS: Array<{
	value: TaskEvaluationMode
	label: string
	short: string
}> = [
	{
		value: 'manual',
		label: 'Ручная проверка',
		short: 'Учитель читает ответ и пишет комментарий.',
	},
	{
		value: 'keywords',
		label: 'Авто по ориентирам',
		short: 'Система ищет ключевые слова и смысловые маркеры.',
	},
]

const CODE_EVALUATION_OPTIONS: Array<{
	value: TaskEvaluationMode
	label: string
	short: string
}> = [
	{
		value: 'stdin_stdout',
		label: 'Автотесты',
		short: 'Код запускается на тестах с входом и ожидаемым выводом.',
	},
]

const LANGUAGE_LABELS: Record<CodeTaskLanguage, string> = {
	python: 'Python',
	javascript: 'JavaScript',
}

const AGE_GROUP_LABELS: Record<'junior' | 'middle' | 'senior', string> = {
	junior: 'Младшая группа',
	middle: 'Средняя группа',
	senior: 'Старшая группа',
}

function splitLines(value: string) {
	return value
		.split('\n')
		.map(item => item.trim())
		.filter(Boolean)
}

function shortenText(value: string, maxLength: number) {
	if (value.length <= maxLength) return value
	return `${value.slice(0, Math.max(0, maxLength - 1)).trimEnd()}…`
}

function getTodayDateKey() {
	const now = new Date()
	const year = now.getFullYear()
	const month = String(now.getMonth() + 1).padStart(2, '0')
	const day = String(now.getDate()).padStart(2, '0')
	return `${year}-${month}-${day}`
}

function isAssignmentOverdue(dueDate: string | null | undefined) {
	if (!dueDate) return false
	const dateKey = dueDate.slice(0, 10)
	if (!/^\d{4}-\d{2}-\d{2}$/.test(dateKey)) return false
	return dateKey < getTodayDateKey()
}

function getAssignmentPendingCount(assignment: AssignmentItem) {
	return Math.max(
		0,
		(assignment.submissions_count || 0) - (assignment.checked_count || 0),
	)
}

async function copyToClipboard(value: string) {
	if (typeof navigator !== 'undefined' && navigator.clipboard?.writeText) {
		await navigator.clipboard.writeText(value)
		return
	}

	if (typeof document === 'undefined') throw new Error('Clipboard unavailable')

	const textarea = document.createElement('textarea')
	textarea.value = value
	textarea.setAttribute('readonly', 'true')
	textarea.style.position = 'absolute'
	textarea.style.left = '-9999px'
	document.body.appendChild(textarea)
	textarea.select()
	document.execCommand('copy')
	document.body.removeChild(textarea)
}

function getJoinRequestStudentName(request: ClassJoinRequestItem) {
	return (
		request.student_full_name ||
		`Ученик #${request.student_id}`
	)
}

function EmptyState({
	title,
	description,
	action,
	className = '',
}: {
	title: string
	description: string
	action?: ReactNode
	className?: string
}) {
	return (
		<div
			className={`rounded-xl border border-dashed border-slate-300 bg-slate-50/80 p-4 text-sm leading-6 text-slate-600 sm:p-5 ${className}`}
		>
			<p className='font-semibold text-slate-900'>{title}</p>
			<p className='mt-1'>{description}</p>
			{action ? <div className='mt-3'>{action}</div> : null}
		</div>
	)
}

function FieldError({ children }: { children: ReactNode }) {
	return <p className='mt-2 text-sm font-semibold text-rose-600'>{children}</p>
}

function getPracticeRisk(
	heatmap: TeacherClassDetail['practice_heatmap'] | undefined,
) {
	if (!heatmap?.assignments.length) {
		return {
			label: 'Нет данных',
			description: 'Практические задания еще не проверялись.',
			className: 'bg-slate-100 text-slate-700',
		}
	}
	if (heatmap.summary.reviewed === 0 || heatmap.summary.failure_rate == null) {
		return {
			label: 'Ждет проверки',
			description: 'Есть практика, но проверенных сдач пока нет.',
			className: 'bg-sky-100 text-sky-700',
		}
	}
	if (heatmap.summary.failure_rate >= 50) {
		return {
			label: 'Высокий риск',
			description: `${heatmap.summary.failure_rate}% проверенных сдач требуют внимания.`,
			className: 'bg-rose-100 text-rose-700',
		}
	}
	if (heatmap.summary.failure_rate >= 25) {
		return {
			label: 'Средний риск',
			description: `${heatmap.summary.failure_rate}% проверенных сдач с ошибками.`,
			className: 'bg-amber-100 text-amber-800',
		}
	}
	return {
		label: 'Стабильно',
		description: `${heatmap.summary.failure_rate}% проверенных сдач с ошибками.`,
		className: 'bg-emerald-100 text-emerald-700',
	}
}

function getSubmissionStatusClass(status: SubmissionItem['status']) {
	if (status === 'checked') return 'bg-emerald-100 text-emerald-700'
	if (status === 'needs_revision') return 'bg-amber-100 text-amber-800'
	return 'bg-sky-100 text-sky-700'
}

function submissionMatchesFilter(
	submission: SubmissionItem,
	filter: SubmissionReviewFilter,
) {
	if (filter === 'pending') return !REVIEWED_SUBMISSION_STATUSES.has(submission.status)
	return submission.status === filter
}

export function TeacherWorkspace({
	initialOverview = null,
}: {
	initialOverview?: TeacherOverviewData | null
}) {
	const [overview, setOverview] = useState<TeacherOverviewData | null>(
		initialOverview,
	)
	const [overviewLoading, setOverviewLoading] = useState(!initialOverview)
	const [overviewError, setOverviewError] = useState<string | null>(null)
	const [joinRequests, setJoinRequests] = useState<ClassJoinRequestItem[]>([])
	const [joinRequestsPagination, setJoinRequestsPagination] = useState<PaginationMeta | null>(null)
	const [joinRequestsPage, setJoinRequestsPage] = useState(1)
	const [joinRequestsLoading, setJoinRequestsLoading] = useState(false)
	const [joinRequestsError, setJoinRequestsError] = useState<string | null>(null)
	const [joinRequestConfirm, setJoinRequestConfirm] = useState<{
		request: ClassJoinRequestItem
		action: JoinRequestAction
	} | null>(null)
	const [joinRequestSubmitting, setJoinRequestSubmitting] = useState(false)
	const [catalog, setCatalog] = useState<LessonCatalogItem[]>([])
	const [catalogPagination, setCatalogPagination] = useState<PaginationMeta | null>(null)
	const [catalogLoading, setCatalogLoading] = useState(false)
	const [catalogError, setCatalogError] = useState<string | null>(null)
	const [selectedClassId, setSelectedClassId] = useState<number | null>(
		initialOverview?.classes[0]?.id ?? null,
	)
	const [selectedClassSnapshot, setSelectedClassSnapshot] = useState<ClassroomItem | null>(initialOverview?.classes[0] ?? null)
	const [classesPage, setClassesPage] = useState(initialOverview?.classes_pagination?.page ?? 1)
	const [studentsPage, setStudentsPage] = useState(1)
	const [assignmentsPage, setAssignmentsPage] = useState(1)
	const [classDetail, setClassDetail] = useState<TeacherClassDetail | null>(
		null,
	)
	const [classDetailLoading, setClassDetailLoading] = useState(false)
	const [classDetailError, setClassDetailError] = useState<string | null>(null)
	const [assignmentRows, setAssignmentRows] = useState<AssignmentItem[]>([])
	const [assignmentsPagination, setAssignmentsPagination] = useState<PaginationMeta | null>(null)
	const [selectedAssignmentId, setSelectedAssignmentId] = useState<
		number | null
	>(null)
	const [submissions, setSubmissions] = useState<SubmissionItem[]>([])
	const [submissionsPagination, setSubmissionsPagination] = useState<PaginationMeta | null>(null)
	const [submissionsPage, setSubmissionsPage] = useState(1)
	const [selectedAssignmentSnapshot, setSelectedAssignmentSnapshot] = useState<AssignmentItem | null>(null)
	const [selectedCatalogLesson, setSelectedCatalogLesson] = useState<LessonCatalogItem | null>(null)
	const [submissionsLoading, setSubmissionsLoading] = useState(false)
	const [submissionsError, setSubmissionsError] = useState<string | null>(null)
	const [feedbackDrafts, setFeedbackDrafts] = useState<Record<number, string>>(
		{},
	)
	const [classForm, setClassForm] = useState({ name: '', description: '' })
	const [assignmentForm, setAssignmentForm] = useState<AssignmentFormState>(
		EMPTY_ASSIGNMENT_FORM,
	)
	const [lessonForm, setLessonForm] =
		useState<LessonFormState>(EMPTY_LESSON_FORM)
	const [lessonBlueprint, setLessonBlueprint] =
		useState<LessonBlueprintKey>('guided')
	const [lessonPracticeMode, setLessonPracticeMode] =
		useState<LessonPracticeMode>('text')
	const [lessonPage, setLessonPage] = useState(1)
	const [lessonSearch, setLessonSearch] = useState('')
	const [lessonSourceFilter, setLessonSourceFilter] =
		useState<LessonSourceFilter>('all')
	const [submissionFilter, setSubmissionFilter] =
		useState<SubmissionReviewFilter>('pending')
	const joinRequestCancelRef = useRef<HTMLButtonElement | null>(null)
	const selectedClassIdRef = useRef<number | null>(selectedClassId)
	const selectedAssignmentIdRef = useRef<number | null>(selectedAssignmentId)
	const classDetailRequestRef = useRef(0)
	const catalogRequestRef = useRef(0)
	const submissionsRequestRef = useRef(0)
	const selectedClass = useMemo<ClassroomItem | undefined>(
		() => overview?.classes.find(item => item.id === selectedClassId) || selectedClassSnapshot || undefined,
		[overview, selectedClassId, selectedClassSnapshot],
	)
	const selectedAssignment = useMemo(
		() => assignmentRows.find(item => item.id === selectedAssignmentId) || (selectedAssignmentSnapshot?.id === selectedAssignmentId ? selectedAssignmentSnapshot : null),
		[assignmentRows, selectedAssignmentId, selectedAssignmentSnapshot],
	)
	const classesWindow = useFiveItemWindow({ items: overview?.classes ?? [], pagination: overview?.classes_pagination, loading: overviewLoading, onPageChange: setClassesPage })
	const requestsWindow = useFiveItemWindow({ items: joinRequests, pagination: joinRequestsPagination, loading: joinRequestsLoading, onPageChange: setJoinRequestsPage })
	const studentsWindow = useFiveItemWindow({ items: classDetail?.students ?? [], pagination: classDetail?.students_pagination, loading: classDetailLoading, onPageChange: setStudentsPage, resetKey: selectedClassId })
	const createLessonHref = selectedClassId
		? `/teacher/lessons/create?classId=${selectedClassId}`
		: '/teacher/lessons/create'
	const selectedClassStudentsCount =
		classDetail?.students_pagination.total ?? selectedClass?.students_count ?? 0
	const selectedClassAssignmentCount =
		assignmentsPagination?.total ?? selectedClass?.assignments_count ?? 0
	const pagePendingSubmissions = useMemo(
		() =>
			assignmentRows.reduce(
				(total, assignment) =>
					total + getAssignmentPendingCount(assignment),
				0,
			),
		[assignmentRows],
	)
	const overdueAssignmentRows = useMemo(
		() => assignmentRows.filter(item => isAssignmentOverdue(item.due_date)),
		[assignmentRows],
	)
	const pageReviewedSubmissions = useMemo(
		() => assignmentRows.reduce((total, item) => total + (item.checked_count || 0), 0),
		[assignmentRows],
	)
	const hasGlobalAssignmentSummary = Boolean(classDetail?.assignment_summary)
	const uncheckedSubmissionsCount = classDetail?.assignment_summary?.pending_submissions ?? pagePendingSubmissions
	const reviewedCount = classDetail?.assignment_summary?.reviewed_submissions ?? pageReviewedSubmissions
	const overdueAssignmentsCount = classDetail?.assignment_summary?.overdue_assignments ?? overdueAssignmentRows.length
	const selectedClassRisk = useMemo(
		() => getPracticeRisk(classDetail?.practice_heatmap),
		[classDetail?.practice_heatmap],
	)
	const filteredLessons = catalog
	const filteredSubmissions = submissions
	const reviewAssignmentRows = useMemo(
		() =>
			[...assignmentRows].sort((a, b) => {
				const pendingDelta =
					getAssignmentPendingCount(b) - getAssignmentPendingCount(a)
				if (pendingDelta !== 0) return pendingDelta

				const overdueDelta =
					Number(isAssignmentOverdue(b.due_date)) -
					Number(isAssignmentOverdue(a.due_date))
				if (overdueDelta !== 0) return overdueDelta

				return (a.due_date || '9999-12-31').localeCompare(
					b.due_date || '9999-12-31',
				)
			}),
		[assignmentRows],
	)
	const assignmentWindow = useFiveItemWindow({ items: reviewAssignmentRows, pagination: assignmentsPagination, loading: classDetailLoading, onPageChange: setAssignmentsPage, resetKey: selectedClassId })
	const catalogWindow = useFiveItemWindow({ items: filteredLessons, pagination: catalogPagination, loading: catalogLoading, onPageChange: setLessonPage, resetKey: `${selectedClassId}|${lessonSearch}|${lessonSourceFilter}` })
	const submissionsWindow = useFiveItemWindow({ items: filteredSubmissions, pagination: submissionsPagination, loading: submissionsLoading, onPageChange: setSubmissionsPage, resetKey: `${selectedAssignmentId}|${submissionFilter}` })
	const attentionCards = useMemo(
		() => [
			{
				key: 'join-requests',
				title: 'Заявки',
				count: joinRequestsPagination?.total ?? joinRequests.length,
				description: joinRequestsLoading
					? 'Проверяем новые заявки учеников.'
					: (joinRequestsPagination?.total ?? joinRequests.length)
						? 'Примите или отклоните заявки, чтобы ученики попали в класс.'
						: 'Новых заявок нет.',
				href: '#teacher-classes',
				action: (joinRequestsPagination?.total ?? joinRequests.length) ? 'Рассмотреть' : 'Открыть классы',
				tone: (joinRequestsPagination?.total ?? joinRequests.length) ? 'sky' : 'slate',
			},
			{
				key: 'submissions',
				title: hasGlobalAssignmentSummary ? 'Проверка' : 'Проверка на странице',
				count: uncheckedSubmissionsCount,
				description: selectedClass
					? uncheckedSubmissionsCount
						? 'Начните с заданий, где больше всего непроверенных ответов.'
						: hasGlobalAssignmentSummary
							? 'По выбранному классу нет срочной проверки.'
							: 'На загруженной странице нет срочной проверки.'
					: 'Выберите класс, чтобы увидеть очередь проверки.',
				href: '#teacher-review',
				action: 'Открыть проверку',
				tone: uncheckedSubmissionsCount ? 'amber' : 'slate',
			},
			{
				key: 'deadlines',
				title: hasGlobalAssignmentSummary ? 'Дедлайны' : 'Дедлайны на странице',
				count: overdueAssignmentsCount,
				description: selectedClass
					? overdueAssignmentsCount
						? 'Просмотрите задания с истекшим сроком и ответами учеников.'
						: hasGlobalAssignmentSummary
							? 'Просроченных заданий по выбранному классу нет.'
							: 'На загруженной странице нет просроченных заданий.'
					: 'После выбора класса здесь появятся сроки заданий.',
				href: '#teacher-review',
				action: 'Посмотреть',
				tone: overdueAssignmentsCount ? 'rose' : 'slate',
			},
		],
		[
			joinRequests.length,
			joinRequestsPagination?.total,
			joinRequestsLoading,
			hasGlobalAssignmentSummary,
			overdueAssignmentsCount,
			selectedClass,
			uncheckedSubmissionsCount,
		],
	)
	const missingClassFields = useMemo(
		() => getMissingClassFields(classForm),
		[classForm],
	)
	const canCreateClass = missingClassFields.length === 0
	const missingAssignmentFields = useMemo(
		() => getMissingAssignmentFields(assignmentForm),
		[assignmentForm],
	)
	const missingAssignmentFieldLabels = useMemo(
		() =>
			missingAssignmentFields.map(
				field => ASSIGNMENT_REQUIRED_FIELD_LABELS[field],
			),
		[missingAssignmentFields],
	)
	const canCreateAssignment =
		Boolean(selectedClassId) && missingAssignmentFields.length === 0
	const selectedLessonForAssignment = useMemo(
		() =>
			catalog.find(lesson => String(lesson.id) === assignmentForm.lesson_id) ||
			(selectedCatalogLesson && String(selectedCatalogLesson.id) === assignmentForm.lesson_id ? selectedCatalogLesson : null),
		[assignmentForm.lesson_id, catalog, selectedCatalogLesson],
	)
	const activeLessonBlueprint = LESSON_BLUEPRINTS[lessonBlueprint]
	const availablePracticeModeOptions = useMemo(
		() =>
			PRACTICE_MODE_OPTIONS.filter(
				item =>
					item.value !== 'code' ||
					ageGroupSupportsCodePractice(lessonForm.age_group),
			),
		[lessonForm.age_group],
	)
	const selectedPracticeMode =
		availablePracticeModeOptions.find(
			item => item.value === lessonPracticeMode,
		) || availablePracticeModeOptions[0]
	const evaluationOptions =
		lessonPracticeMode === 'code'
			? CODE_EVALUATION_OPTIONS
			: TEXT_EVALUATION_OPTIONS
	const selectedEvaluationMode =
		evaluationOptions.find(item => item.value === lessonForm.evaluation_mode) ||
		evaluationOptions[0]
	const lessonKeyPoints = useMemo(
		() => splitLines(lessonForm.key_points),
		[lessonForm.key_points],
	)
	const lessonInteractiveSteps = useMemo(
		() => splitLines(lessonForm.interactive_steps),
		[lessonForm.interactive_steps],
	)
	const lessonTaskHints = useMemo(
		() => splitLines(lessonForm.task_hints),
		[lessonForm.task_hints],
	)
	const lessonAnswerKeywords = useMemo(
		() =>
			lessonForm.answer_keywords
				.split(',')
				.map(item => item.trim())
				.filter(Boolean),
		[lessonForm.answer_keywords],
	)
	const configuredJudgeTests = useMemo(
		() =>
			lessonForm.judge_tests.filter(
				item => item.input.trim() || item.expected.trim(),
			),
		[lessonForm.judge_tests],
	)
	const lessonPreviewTitle =
		lessonForm.title.trim() ||
		activeLessonBlueprint.sampleTitle[lessonForm.age_group]
	const lessonPreviewSummary =
		lessonForm.summary.trim() ||
		activeLessonBlueprint.summary(lessonPreviewTitle)
	const lessonHasPractice = lessonPracticeMode !== 'none'
	const lessonProgress = useMemo(
		() => [
			{
				label: 'Основа урока',
				done: Boolean(lessonForm.title.trim() && lessonForm.summary.trim()),
				detail: 'Название и краткое описание',
			},
			{
				label: 'Подача темы',
				done: Boolean(
					lessonForm.theory_text.trim() || lessonKeyPoints.length >= 3,
				),
				detail: 'Объяснение или тезисы',
			},
			{
				label: 'Маршрут урока',
				done: lessonInteractiveSteps.length >= 2,
				detail: 'Минимум два шага разбора',
			},
			{
				label: 'Практика',
				done: lessonHasPractice
					? Boolean(
							(lessonForm.task_title.trim() || lessonForm.task_prompt.trim()) &&
							(lessonPracticeMode === 'code'
								? configuredJudgeTests.length > 0
								: lessonForm.evaluation_mode === 'manual' ||
									(lessonForm.evaluation_mode === 'keywords' &&
										lessonAnswerKeywords.length > 0) ||
									(lessonForm.evaluation_mode === 'stdin_stdout' &&
										configuredJudgeTests.length > 0)),
						)
					: true,
				detail: lessonHasPractice
					? lessonPracticeMode === 'code'
						? 'Есть кодовая задача и как минимум один автотест'
						: lessonForm.evaluation_mode === 'stdin_stdout'
							? 'Есть задача и как минимум один автотест'
							: lessonForm.evaluation_mode === 'keywords'
								? 'Есть задача и ориентиры для автопроверки'
								: 'Есть задача для ручной проверки'
					: 'Практика вынесена отдельно',
			},
		],
		[
			configuredJudgeTests.length,
			lessonAnswerKeywords.length,
			lessonForm.evaluation_mode,
			lessonForm.summary,
			lessonForm.task_prompt,
			lessonForm.task_title,
			lessonForm.theory_text,
			lessonForm.title,
			lessonHasPractice,
			lessonInteractiveSteps.length,
			lessonKeyPoints.length,
		],
	)
	const lessonCompletion = Math.round(
		(lessonProgress.filter(item => item.done).length / lessonProgress.length) *
			100,
	)
	async function handleCopyClassCode(code: string) {
		try {
			await copyToClipboard(code)
			showSuccessToast(`Код класса ${code} скопирован.`)
		} catch {
			showErrorToast('Не удалось скопировать код класса.')
		}
	}

	function selectClass(nextClassId: number | null) {
		if (selectedClassIdRef.current === nextClassId) return
		selectedClassIdRef.current = nextClassId
		classDetailRequestRef.current += 1
		catalogRequestRef.current += 1
		submissionsRequestRef.current += 1
		selectedAssignmentIdRef.current = null
		setSelectedClassId(nextClassId)
		setSelectedClassSnapshot(overview?.classes.find(item => item.id === nextClassId) ?? null)
		setStudentsPage(1)
		setAssignmentsPage(1)
		setLessonPage(1)
		setClassDetail(null)
		setClassDetailError(null)
		setClassDetailLoading(Boolean(nextClassId))
		setCatalog([])
		setCatalogError(null)
		setCatalogLoading(Boolean(nextClassId))
		setAssignmentRows([])
		setAssignmentsPagination(null)
		setSelectedAssignmentId(null)
		setSelectedAssignmentSnapshot(null)
		setSelectedCatalogLesson(null)
		setAssignmentForm(current => ({ ...current, lesson_id: '' }))
		setSubmissions([])
		setSubmissionsPagination(null)
		setSubmissionsPage(1)
		setFeedbackDrafts({})
		setSubmissionsError(null)
		setSubmissionsLoading(false)
	}

	function selectAssignment(nextAssignmentId: number | null) {
		if (selectedAssignmentIdRef.current === nextAssignmentId) return
		selectedAssignmentIdRef.current = nextAssignmentId
		submissionsRequestRef.current += 1
		setSelectedAssignmentId(nextAssignmentId)
		setSelectedAssignmentSnapshot(assignmentRows.find(item => item.id === nextAssignmentId) ?? null)
		setSubmissionsPage(1)
		setSubmissions([])
		setFeedbackDrafts({})
		setSubmissionsError(null)
		setSubmissionsLoading(Boolean(nextAssignmentId))
	}

	useEffect(() => {
		setLessonPage(1)
	}, [selectedClassId, lessonSearch, lessonSourceFilter])

	useEffect(() => {
		if (!joinRequestConfirm) return
		window.setTimeout(() => joinRequestCancelRef.current?.focus(), 0)
	}, [joinRequestConfirm])

	useEffect(() => {
		if (
			!ageGroupSupportsCodePractice(lessonForm.age_group) &&
			lessonPracticeMode === 'code'
		) {
			setLessonPracticeMode('text')
		}
	}, [lessonForm.age_group, lessonPracticeMode])

	useEffect(() => {
		setLessonForm(current => {
			if (lessonPracticeMode === 'none') {
				if (
					current.evaluation_mode === 'manual' &&
					current.judge_tests.length === 0
				) {
					return current
				}
				return {
					...current,
					evaluation_mode: 'manual',
					judge_tests: [],
				}
			}
			if (lessonPracticeMode === 'code') {
				if (current.evaluation_mode !== 'stdin_stdout') {
					return {
						...current,
						evaluation_mode: 'stdin_stdout',
						judge_tests:
							current.judge_tests.length > 0
								? current.judge_tests
								: [createEmptyJudgeTest()],
					}
				}
				if (
					current.evaluation_mode === 'stdin_stdout' &&
					current.judge_tests.length === 0
				) {
					return {
						...current,
						judge_tests: [createEmptyJudgeTest()],
					}
				}
				return current
			}
			if (current.evaluation_mode === 'stdin_stdout') {
				return {
					...current,
					evaluation_mode: 'manual',
					judge_tests: [],
				}
			}
			return current
		})
	}, [lessonPracticeMode])

	function patchAssignmentStats(assignmentId: number, nextAssignment: AssignmentItem) {
		setAssignmentRows(current =>
			current.map(assignment =>
				assignment.id === assignmentId ? { ...assignment, ...nextAssignment } : assignment,
			),
		)
	}

	function addJudgeTest() {
		setLessonForm(current => ({
			...current,
			judge_tests: [...current.judge_tests, createEmptyJudgeTest()],
		}))
	}

	function updateJudgeTest(index: number, patch: Partial<LessonJudgeTestCase>) {
		setLessonForm(current => ({
			...current,
			judge_tests: current.judge_tests.map((item, itemIndex) =>
				itemIndex === index ? { ...item, ...patch } : item,
			),
		}))
	}

	function removeJudgeTest(index: number) {
		setLessonForm(current => ({
			...current,
			judge_tests: current.judge_tests.filter(
				(_, itemIndex) => itemIndex !== index,
			),
		}))
	}

	function applyAssignmentTemplate(
		type: AssignmentType,
		replaceFilledFields = false,
	) {
		const template = ASSIGNMENT_TEMPLATES[type]
		const lessonAwareTitle =
			type === 'lesson_practice' && selectedLessonForAssignment
				? `Задание по уроку: ${selectedLessonForAssignment.title}`
				: template.title
		const lessonAwareDescription =
			type === 'lesson_practice' && selectedLessonForAssignment
				? selectedLessonForAssignment.summary
				: template.description

		setAssignmentForm(current => {
			const useTemplate = (value: string) =>
				replaceFilledFields || !value.trim()
			return {
				...current,
				assignment_type: type,
				submission_format: template.submission_format,
				title: useTemplate(current.title) ? lessonAwareTitle : current.title,
				description: useTemplate(current.description)
					? lessonAwareDescription
					: current.description,
				learning_goal: useTemplate(current.learning_goal)
					? template.learning_goal
					: current.learning_goal,
				work_steps: useTemplate(current.work_steps)
					? template.work_steps
					: current.work_steps,
				success_criteria: useTemplate(current.success_criteria)
					? template.success_criteria
					: current.success_criteria,
				resources: useTemplate(current.resources)
					? template.resources
					: current.resources,
			}
		})
	}

	function selectLessonForAssignment(lesson: LessonCatalogItem) {
		setSelectedCatalogLesson(lesson)
		setAssignmentForm(current => ({
			...current,
			assignment_type: 'lesson_practice',
			submission_format: ASSIGNMENT_TEMPLATES.lesson_practice.submission_format,
			lesson_id: String(lesson.id),
			title: current.title || `Задание по уроку: ${lesson.title}`,
			description: current.description || lesson.summary,
			learning_goal:
				current.learning_goal ||
				ASSIGNMENT_TEMPLATES.lesson_practice.learning_goal,
			work_steps:
				current.work_steps || ASSIGNMENT_TEMPLATES.lesson_practice.work_steps,
			success_criteria:
				current.success_criteria ||
				ASSIGNMENT_TEMPLATES.lesson_practice.success_criteria,
		}))
	}

	function setAssignmentLesson(nextLessonId: string) {
		setSelectedCatalogLesson(
			catalog.find(lesson => String(lesson.id) === nextLessonId) ?? null,
		)
		setAssignmentForm(current => ({ ...current, lesson_id: nextLessonId }))
	}

	function applyLessonBlueprint(replaceFilledFields = false) {
		const template = LESSON_BLUEPRINTS[lessonBlueprint]
		setLessonForm(current => {
			const useTemplate = (value: string) =>
				replaceFilledFields || !value.trim()
			const nextTitle = useTemplate(current.title)
				? template.sampleTitle[current.age_group]
				: current.title
			const theme = nextTitle.trim() || template.sampleTitle[current.age_group]
			return {
				...current,
				title: nextTitle,
				summary: useTemplate(current.summary)
					? template.summary(theme)
					: current.summary,
				theory_text: useTemplate(current.theory_text)
					? template.theory(theme)
					: current.theory_text,
				key_points: useTemplate(current.key_points)
					? template.keyPoints
					: current.key_points,
				interactive_steps: useTemplate(current.interactive_steps)
					? template.steps
					: current.interactive_steps,
				task_title: useTemplate(current.task_title)
					? template.taskTitle(theme)
					: current.task_title,
				task_prompt: useTemplate(current.task_prompt)
					? template.taskPrompt(theme)
					: current.task_prompt,
				answer_keywords: useTemplate(current.answer_keywords)
					? template.keywords
					: current.answer_keywords,
				task_hints: useTemplate(current.task_hints)
					? template.hints
					: current.task_hints,
				starter_code:
					lessonPracticeMode === 'code' && useTemplate(current.starter_code)
						? template.starterCode
						: current.starter_code,
				duration_minutes: useTemplate(current.duration_minutes)
					? template.durationByAge[current.age_group]
					: current.duration_minutes,
				passing_score: useTemplate(current.passing_score)
					? template.passingScore
					: current.passing_score,
				task_xp_reward: useTemplate(current.task_xp_reward)
					? template.taskXpReward
					: current.task_xp_reward,
			}
		})
	}

	function applyLessonRecommendations() {
		const template = LESSON_BLUEPRINTS[lessonBlueprint]
		setLessonForm(current => ({
			...current,
			duration_minutes: template.durationByAge[current.age_group],
			passing_score: template.passingScore,
			task_xp_reward: template.taskXpReward,
			starter_code:
				lessonPracticeMode === 'code' && !current.starter_code.trim()
					? template.starterCode
					: current.starter_code,
			programming_language:
				lessonPracticeMode === 'code'
					? current.programming_language
					: defaultProgrammingLanguage(current.age_group),
			time_limit_ms: current.time_limit_ms.trim() || '2000',
			memory_limit_mb: current.memory_limit_mb.trim() || '128',
			judge_tests:
				lessonPracticeMode === 'code' &&
				current.evaluation_mode === 'stdin_stdout' &&
				current.judge_tests.length === 0
					? [createEmptyJudgeTest()]
					: current.judge_tests,
		}))
	}

	function resetLessonComposer() {
		const nextForm = buildEmptyLessonForm(
			lessonForm.age_group,
			lessonPracticeMode,
		)
		setLessonForm({
			...nextForm,
			duration_minutes:
				activeLessonBlueprint.durationByAge[lessonForm.age_group],
			passing_score: activeLessonBlueprint.passingScore,
			task_xp_reward: activeLessonBlueprint.taskXpReward,
			starter_code:
				lessonPracticeMode === 'code' ? activeLessonBlueprint.starterCode : '',
		})
	}

	async function loadJoinRequests(options: { silent?: boolean; page?: number } = {}) {
		const requestedPage = options.page ?? joinRequestsPage
		if (!options.silent) {
			setJoinRequestsLoading(true)
		}
		setJoinRequestsError(null)
		try {
			const data = await api<TeacherJoinRequestsResponse>(
				`/teacher/join-requests?page=${requestedPage}&page_size=${SERVER_PAGE_SIZE}`,
				undefined,
				'required',
			)
			setJoinRequests(data.requests)
			setJoinRequestsPagination(data.pagination)
			const clampedPage = clampPageToPagination(requestedPage, data.pagination)
			if (clampedPage !== requestedPage) setJoinRequestsPage(clampedPage)
			return data
		} catch (error) {
			const message = getApiErrorMessage(
				error,
				'Не удалось загрузить заявки на вступление.',
			)
			if (!options.silent) {
				setJoinRequestsError(message)
			}
			throw error
		} finally {
			if (!options.silent) {
				setJoinRequestsLoading(false)
			}
		}
	}

	async function loadOverview(nextPage = classesPage) {
		setOverviewLoading(true)
		setOverviewError(null)
		try {
			const data = await api<TeacherOverviewData>(
				`/teacher/overview?page=${nextPage}&page_size=${SERVER_PAGE_SIZE}`,
				undefined,
				'required',
			)
			setOverview(data)
			if (!selectedClassId && data.classes[0]) {
				selectClass(data.classes[0].id)
			}
		} catch (error) {
			const message = getApiErrorMessage(
				error,
				'Не удалось загрузить кабинет учителя.',
			)
			setOverviewError(message)
			throw error
		} finally {
			setOverviewLoading(false)
		}
	}

	async function loadCatalog(classroomId: number, nextPage = lessonPage) {
		const requestId = ++catalogRequestRef.current
		setCatalogLoading(true)
		setCatalogError(null)
		try {
			const params = new URLSearchParams({
				classroom_id: String(classroomId),
				page: String(nextPage),
				page_size: String(SERVER_PAGE_SIZE),
				source: lessonSourceFilter,
				q: lessonSearch.trim(),
			})
			const data = await api<TeacherLessonCatalogResponse>(
				`/teacher/lesson-catalog?${params.toString()}`,
				undefined,
				'required',
			)
			if (
				requestId !== catalogRequestRef.current ||
				selectedClassIdRef.current !== classroomId
			) {
				return
			}
			setCatalog(data.lessons)
			setCatalogPagination(data.pagination)
		} catch (error) {
			if (
				requestId !== catalogRequestRef.current ||
				selectedClassIdRef.current !== classroomId
			) {
				return
			}
			const message = getApiErrorMessage(
				error,
				'Не удалось загрузить библиотеку уроков.',
			)
			setCatalogError(message)
			throw error
		} finally {
			if (
				requestId === catalogRequestRef.current &&
				selectedClassIdRef.current === classroomId
			) {
				setCatalogLoading(false)
			}
		}
	}

	async function loadClassDetails(classroomId: number, nextStudentsPage = studentsPage, nextAssignmentsPage = assignmentsPage) {
		const requestId = ++classDetailRequestRef.current
		setClassDetailLoading(true)
		setClassDetailError(null)
		try {
			const [detail, nextOverview] = await Promise.all([
				api<TeacherClassDetail>(
					`/teacher/classes/${classroomId}?students_page=${nextStudentsPage}&assignments_page=${nextAssignmentsPage}&page_size=${SERVER_PAGE_SIZE}`,
					undefined,
					'required',
				),
				api<TeacherOverviewData>(`/teacher/overview?page=${classesPage}&page_size=${SERVER_PAGE_SIZE}`, undefined, 'required'),
			])
			if (
				requestId !== classDetailRequestRef.current ||
				selectedClassIdRef.current !== classroomId
			) {
				return
			}
			setClassDetail(detail)
			setAssignmentRows(detail.assignments)
			setAssignmentsPagination(detail.assignments_pagination)
			setOverview(nextOverview)
			setSelectedAssignmentId(current => {
				const nextAssignmentId = (
					current
				)
					? current
					: detail.assignments[0]?.id ?? null
				selectedAssignmentIdRef.current = nextAssignmentId
				if (!current) setSelectedAssignmentSnapshot(detail.assignments[0] ?? null)
				return nextAssignmentId
			})
		} catch (error) {
			if (
				requestId !== classDetailRequestRef.current ||
				selectedClassIdRef.current !== classroomId
			) {
				return
			}
			const message = getApiErrorMessage(
				error,
				'Не удалось загрузить данные выбранного класса.',
			)
			setClassDetailError(message)
			throw error
		} finally {
			if (
				requestId === classDetailRequestRef.current &&
				selectedClassIdRef.current === classroomId
			) {
				setClassDetailLoading(false)
			}
		}
	}

	async function loadSubmissions(assignmentId: number, nextPage = submissionsPage) {
		const requestId = ++submissionsRequestRef.current
		setSubmissionsLoading(true)
		setSubmissionsError(null)
		try {
			const [data, nextOverview] = await Promise.all([
				api<TeacherSubmissionsResponse>(
					`/teacher/assignments/${assignmentId}/submissions?page=${nextPage}&page_size=${SERVER_PAGE_SIZE}&status=${submissionFilter}`,
					undefined,
					'required',
				),
				api<TeacherOverviewData>(`/teacher/overview?page=${classesPage}&page_size=${SERVER_PAGE_SIZE}`, undefined, 'required'),
			])
			if (
				requestId !== submissionsRequestRef.current ||
				selectedAssignmentIdRef.current !== assignmentId
			) {
				return
			}
			setSubmissions(data.submissions)
			setSubmissionsPagination(data.pagination)
			const clampedPage = clampPageToPagination(nextPage, data.pagination)
			if (clampedPage !== nextPage) setSubmissionsPage(clampedPage)
			setFeedbackDrafts(
				data.submissions.reduce<Record<number, string>>((acc, submission) => {
					acc[submission.id] = submission.feedback || ''
					return acc
				}, {}),
			)
			patchAssignmentStats(assignmentId, data.assignment)
			setOverview(nextOverview)
			return data
		} catch (error) {
			if (
				requestId !== submissionsRequestRef.current ||
				selectedAssignmentIdRef.current !== assignmentId
			) {
				return
			}
			const message = getApiErrorMessage(
				error,
				'Не удалось загрузить ответы учеников по заданию.',
			)
			setSubmissionsError(message)
			throw error
		} finally {
			if (
				requestId === submissionsRequestRef.current &&
				selectedAssignmentIdRef.current === assignmentId
			) {
				setSubmissionsLoading(false)
			}
		}
	}

	async function confirmJoinRequestDecision() {
		if (!joinRequestConfirm) return

		const { request: joinRequest, action } = joinRequestConfirm
		setJoinRequestSubmitting(true)
		try {
			await api(
				`/teacher/join-requests/${joinRequest.id}/${action === 'approve' ? 'approve' : 'reject'}`,
				{ method: 'POST' },
				'required',
			)
			showSuccessToast(
				action === 'approve'
					? 'Ученик добавлен в класс.'
					: 'Заявка отклонена.',
			)
			setJoinRequestConfirm(null)
			if (selectedClassId) {
				await Promise.all([loadJoinRequests(), loadClassDetails(selectedClassId)])
			} else {
				await Promise.all([loadJoinRequests(), loadOverview()])
			}
		} catch (error) {
			showErrorToast(
				error instanceof Error ? error.message : 'Не удалось обработать заявку.',
			)
		} finally {
			setJoinRequestSubmitting(false)
		}
	}

	useEffect(() => {
		if (initialOverview && classesPage === initialOverview.classes_pagination?.page) return
		loadOverview(classesPage).catch(() =>
			showErrorToast(
				'Не удалось загрузить кабинет учителя. Проверьте авторизацию и попробуйте снова.',
			),
		)
	}, [classesPage, initialOverview])

	useEffect(() => {
		loadJoinRequests({ page: joinRequestsPage }).catch(() =>
			showErrorToast('Не удалось загрузить заявки на вступление.'),
		)
		const intervalId = window.setInterval(() => {
			loadJoinRequests({ silent: true, page: joinRequestsPage }).catch(() => undefined)
		}, 25000)
		return () => window.clearInterval(intervalId)
	}, [joinRequestsPage])

	useEffect(() => {
		selectedClassIdRef.current = selectedClassId
		if (!selectedClassId) {
			classDetailRequestRef.current += 1
			catalogRequestRef.current += 1
			setCatalog([])
			setCatalogPagination(null)
			setCatalogError(null)
			setCatalogLoading(false)
			setClassDetail(null)
			setClassDetailError(null)
			setClassDetailLoading(false)
			setAssignmentRows([])
			setAssignmentsPagination(null)
			selectAssignment(null)
			return
		}
		loadClassDetails(selectedClassId, studentsPage, assignmentsPage).catch(() => {
			showErrorToast('Не удалось загрузить учеников и задания выбранного класса.')
		})
	}, [assignmentsPage, selectedClassId, studentsPage])

	useEffect(() => {
		if (!selectedClassId) return
		const timer = window.setTimeout(() => {
			loadCatalog(selectedClassId, lessonPage).catch(() => {
				showErrorToast('Не удалось загрузить уроки выбранного класса.')
			})
		}, 250)
		return () => window.clearTimeout(timer)
	}, [lessonPage, lessonSearch, lessonSourceFilter, selectedClassId])

	useEffect(() => {
		selectedAssignmentIdRef.current = selectedAssignmentId
		if (selectedAssignmentId) {
			loadSubmissions(selectedAssignmentId, submissionsPage).catch((error) => {
				setSubmissions([])
				setFeedbackDrafts({})
				showErrorToast(
					getApiErrorMessage(
						error,
						'Не удалось загрузить ответы учеников по заданию.',
					),
				)
			})
			return
		}
		submissionsRequestRef.current += 1
		setSubmissions([])
		setSubmissionsPagination(null)
		setFeedbackDrafts({})
		setSubmissionsError(null)
		setSubmissionsLoading(false)
	}, [selectedAssignmentId, submissionFilter, submissionsPage])

	async function createClass(event: FormEvent) {
		event.preventDefault()
		if (missingClassFields.length > 0) {
			showErrorToast(
				`Заполните обязательные поля: ${missingClassFields.map(field => CLASS_REQUIRED_FIELD_LABELS[field]).join(', ')}.`,
			)
			return
		}

		try {
			await api(
				'/teacher/classes',
				{
					method: 'POST',
					body: JSON.stringify({
						name: classForm.name.trim(),
						description: classForm.description.trim(),
					}),
				},
				'required',
			)
			setClassForm({ name: '', description: '' })
			showSuccessToast('Класс создан.')
			await loadOverview()
		} catch (error) {
			showErrorToast(error instanceof Error ? error.message : 'Не удалось создать класс.')
		}
	}

	async function createAssignment(event: FormEvent) {
		event.preventDefault()
		if (!selectedClassId) {
			showErrorToast('Сначала выберите класс, для которого создается задание.')
			return
		}
		if (missingAssignmentFields.length > 0) {
			showErrorToast(
				`Заполните обязательные поля: ${missingAssignmentFieldLabels.join(', ')}.`,
			)
			return
		}
		try {
			await api(
				`/teacher/classes/${selectedClassId}/assignments`,
				{
					method: 'POST',
					body: JSON.stringify({
						...assignmentForm,
						lesson_id: Number(assignmentForm.lesson_id),
					}),
				},
				true,
			)
			setAssignmentForm(current => ({
				...EMPTY_ASSIGNMENT_FORM,
				assignment_type: current.assignment_type,
				submission_format: current.submission_format,
				lesson_id: current.lesson_id,
			}))
			showSuccessToast('Задание назначено классу.')
			await loadClassDetails(selectedClassId)
		} catch (error) {
			showErrorToast(error instanceof Error ? error.message : 'Не удалось назначить задание классу.')
		}
	}

	async function gradeSubmission(
		submissionId: number,
		status: 'checked' | 'needs_revision',
		currentScore: number,
		currentFeedback?: string | null,
	) {
		try {
			await api(
				`/teacher/submissions/${submissionId}/grade`,
				{
					method: 'PATCH',
					body: JSON.stringify({
						score: currentScore,
						feedback:
							currentFeedback ||
							(status === 'checked'
								? 'Урок выполнен верно.'
								: 'Нужно доработать и отправить ещё раз.'),
						status,
					}),
				},
				true,
			)
			showSuccessToast(
				status === 'checked'
					? 'Урок отмечен как выполненный.'
					: 'Урок отправлен на доработку.',
			)
			if (selectedAssignmentId) {
				await Promise.all([
					loadSubmissions(selectedAssignmentId),
					...(selectedClassId
						? [loadClassDetails(selectedClassId)]
						: []),
				])
			}
		} catch (error) {
			showErrorToast(error instanceof Error ? error.message : 'Не удалось обновить статус сдачи.')
		}
	}

	return (
		<div className='teacher-workspace space-y-6'>
			<nav
				aria-label='Зоны кабинета учителя'
				className='teacher-workspace__panel codequest-card flex flex-wrap gap-2 p-3'
			>
				{TEACHER_ZONES.map(zone => (
					<a
						key={zone.id}
						href={`#${zone.id}`}
						className='rounded-full px-4 py-2 text-sm font-bold text-slate-600 transition hover:bg-slate-100 hover:text-slate-900 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-sky-500'
					>
						{zone.label}
					</a>
				))}
			</nav>

			<section
				className='teacher-workspace__panel codequest-card border border-slate-200/80 bg-white/95 p-3 shadow-sm lg:sticky lg:top-3 lg:z-30'
				aria-label='Быстрый контекст выбранного класса'
			>
				<div className='flex flex-col gap-3 xl:flex-row xl:items-center xl:justify-between'>
					<div className='flex min-w-0 items-center gap-3'>
						<div className='flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl bg-slate-900 text-sm font-black text-white'>
							{selectedClass?.name?.slice(0, 1).toUpperCase() || 'К'}
						</div>
						<div className='min-w-0'>
							<p className='text-xs font-bold uppercase tracking-[0.14em] text-slate-500'>
								Активный класс
							</p>
							<p className='truncate text-base font-black text-slate-900 sm:text-lg'>
								{selectedClass?.name || 'Выберите класс'}
							</p>
						</div>
					</div>

					<div className='grid grid-cols-2 gap-2 text-sm sm:grid-cols-4 xl:min-w-[30rem]'>
						<div className='rounded-2xl bg-slate-50 px-3 py-2'>
							<p className='text-xs font-bold uppercase tracking-[0.12em] text-slate-400'>
								Код
							</p>
							<p className='truncate font-mono font-black text-slate-900'>
								{selectedClass?.code || '—'}
							</p>
						</div>
						<div className='rounded-2xl bg-slate-50 px-3 py-2'>
							<p className='text-xs font-bold uppercase tracking-[0.12em] text-slate-400'>
								Ученики
							</p>
							<p className='font-black text-slate-900'>
								{selectedClassStudentsCount}
							</p>
						</div>
						<div className='rounded-2xl bg-slate-50 px-3 py-2'>
							<p className='text-xs font-bold uppercase tracking-[0.12em] text-slate-400'>
								{hasGlobalAssignmentSummary ? 'Проверка' : 'Проверка на странице'}
							</p>
							<p className='font-black text-slate-900'>
								{uncheckedSubmissionsCount}
							</p>
						</div>
						<div className='rounded-2xl bg-slate-50 px-3 py-2'>
							<p className='text-xs font-bold uppercase tracking-[0.12em] text-slate-400'>
								Риск
							</p>
							<span
								className={`mt-1 inline-flex rounded-full px-2.5 py-1 text-xs font-bold ${selectedClassRisk.className}`}
							>
								{selectedClassRisk.label}
							</span>
						</div>
					</div>

					<div className='flex flex-wrap gap-2 xl:justify-end'>
						<Link
							href='/teacher/lessons'
							className='inline-flex min-h-10 flex-1 items-center justify-center gap-2 rounded-full border border-slate-200 bg-white px-4 text-sm font-semibold text-slate-700 transition hover:border-slate-300 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-sky-500 sm:flex-none'
						>
							<ListChecks className='h-4 w-4' />
							Черновики и уроки
						</Link>
						<Link
							href={createLessonHref}
							className='inline-flex min-h-10 flex-1 items-center justify-center gap-2 rounded-full bg-sky-600 px-4 text-sm font-semibold text-white transition hover:bg-sky-700 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-sky-500 sm:flex-none'
						>
							<FilePlus2 className='h-4 w-4' />
							Урок
						</Link>
						<a
							href='#teacher-assignments'
							className='inline-flex min-h-10 flex-1 items-center justify-center gap-2 rounded-full bg-slate-900 px-4 text-sm font-semibold text-white transition hover:bg-slate-800 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-slate-500 sm:flex-none'
						>
							<ClipboardCheck className='h-4 w-4' />
							Задание
						</a>
						<button
							type='button'
							disabled={!selectedClass}
							onClick={() =>
								selectedClass ? handleCopyClassCode(selectedClass.code) : undefined
							}
							className='inline-flex min-h-10 flex-1 items-center justify-center gap-2 rounded-full border border-slate-200 bg-white px-4 text-sm font-semibold text-slate-700 transition hover:border-slate-300 disabled:cursor-not-allowed disabled:opacity-50 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-sky-500 sm:flex-none'
						>
							<Copy className='h-4 w-4' />
							Код
						</button>
					</div>
				</div>
			</section>

			<section
				className='teacher-workspace__panel codequest-card p-6'
				aria-labelledby='selected-class-context-title'
			>
				<div className='flex flex-col gap-5 xl:flex-row xl:items-start xl:justify-between'>
					<div className='min-w-0'>
						<p className='text-sm font-bold uppercase tracking-[0.2em] text-emerald-600'>
							Выбранный класс
						</p>
						<h2
							id='selected-class-context-title'
							className='mt-2 break-words text-2xl font-black text-slate-900 sm:text-3xl'
						>
							{selectedClass?.name || 'Класс не выбран'}
						</h2>
						<p className='mt-3 max-w-3xl text-sm leading-6 text-slate-600'>
							{selectedClass
								? classDetail?.classroom.description ||
									'Все панели ниже работают с этим классом: уроки, задания, ученики и проверка.'
								: overview?.classes.length
									? 'Выберите класс в зоне «Классы», чтобы открыть ученикам уроки и задания.'
									: 'Создайте первый класс, чтобы получить код входа и начать назначать уроки.'}
						</p>
					</div>

				</div>

				<div className='mt-5 grid gap-3 sm:grid-cols-2 xl:grid-cols-5'>
					<div className='rounded-2xl border border-slate-200 bg-slate-50 p-4'>
						<p className='text-xs font-bold uppercase tracking-[0.16em] text-slate-500'>
							Код
						</p>
						<p className='mt-2 break-all font-mono text-lg font-black text-slate-900'>
							{selectedClass?.code || '—'}
						</p>
					</div>
					<div className='rounded-2xl border border-slate-200 bg-slate-50 p-4'>
						<p className='text-xs font-bold uppercase tracking-[0.16em] text-slate-500'>
							Ученики
						</p>
						<p className='mt-2 text-3xl font-black text-slate-900'>
							{selectedClassStudentsCount}
						</p>
					</div>
					<div className='rounded-2xl border border-slate-200 bg-slate-50 p-4'>
						<p className='text-xs font-bold uppercase tracking-[0.16em] text-slate-500'>
							Задания
						</p>
						<p className='mt-2 text-3xl font-black text-slate-900'>
							{selectedClassAssignmentCount}
						</p>
					</div>
					<div className='rounded-2xl border border-slate-200 bg-slate-50 p-4'>
						<p className='text-xs font-bold uppercase tracking-[0.16em] text-slate-500'>
							{hasGlobalAssignmentSummary ? 'Проверено' : 'Проверено на странице'}
						</p>
						<p className='mt-2 text-3xl font-black text-slate-900'>
							{reviewedCount}
						</p>
					</div>
					<div className='rounded-2xl border border-slate-200 bg-slate-50 p-4'>
						<p className='text-xs font-bold uppercase tracking-[0.16em] text-slate-500'>
							Практика
						</p>
						<span
							className={`mt-2 inline-flex rounded-full px-3 py-1 text-sm font-bold ${selectedClassRisk.className}`}
						>
							{selectedClassRisk.label}
						</span>
						<p className='mt-2 text-xs leading-5 text-slate-500'>
							{selectedClassRisk.description}
						</p>
					</div>
				</div>

				{classDetail?.practice_heatmap?.assignments.length ? (
					<div className='mt-4 border-t border-slate-100 pt-3'>
						<div className='flex flex-wrap items-center justify-between gap-2 gap-y-1 text-xs text-slate-500'>
							<span className='font-medium text-slate-600'>
								Тепловая карта практики
							</span>
							<span className='text-right'>
								{classDetail.practice_heatmap.summary.reviewed > 0 ? (
									<>
										{classDetail.practice_heatmap.summary.failed} из{' '}
										{classDetail.practice_heatmap.summary.reviewed} проверенных
										требуют внимания
									</>
								) : (
									<>проверенных сдач пока нет</>
								)}
							</span>
						</div>
						<div
							className='mt-2 flex max-w-full gap-px overflow-x-auto pb-0.5'
							role='list'
							aria-label='Доля ошибок по заданиям практики'
						>
							{classDetail.practice_heatmap.assignments.map(row => (
								<button
									key={row.assignment_id}
									type='button'
									role='listitem'
									title={`${row.title}\nНеверно: ${row.failed}, проверено: ${row.reviewed}${
										row.failure_rate != null ? ` (${row.failure_rate}%)` : ''
									}\nНажмите, чтобы открыть сдачи`}
									onClick={() => selectAssignment(row.assignment_id)}
									className='min-h-6 min-w-[8px] flex-1 rounded-sm transition hover:opacity-90 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-sky-500 sm:max-w-[100px]'
									style={{
										backgroundColor: practiceHeatSegmentColor(
											row.failure_rate,
											row.reviewed,
										),
									}}
								/>
							))}
						</div>
					</div>
				) : null}
			</section>

			<section
				id='teacher-overview'
				className='teacher-workspace__panel codequest-card p-6 scroll-mt-24'
				aria-labelledby='teacher-overview-title'
			>
				<div className='flex flex-wrap items-center justify-between gap-3'>
					<div>
						<p className='text-sm font-bold uppercase tracking-[0.2em] text-emerald-600'>
							Главное
						</p>
						<h2
							id='teacher-overview-title'
							className='mt-2 text-2xl font-black text-slate-900'
						>
							Что требует внимания
						</h2>
					</div>
					{overviewLoading ? (
						<span className='rounded-full bg-slate-100 px-4 py-2 text-sm font-semibold text-slate-600'>
							Загружаем кабинет...
						</span>
					) : null}
				</div>

				{overviewError ? (
					<div className='mt-5 rounded-2xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-700'>
						{overviewError}
					</div>
				) : null}

				<div className='mt-5 rounded-3xl border border-slate-200 bg-slate-50/80 p-4'>
					<div className='flex flex-wrap items-center justify-between gap-3'>
						<div>
							<p className='text-base font-black text-slate-900'>
								Очередь на сегодня
							</p>
							<p className='mt-1 text-sm leading-6 text-slate-600'>
								Сначала разберите заявки, затем непроверенные ответы и
								просроченные дедлайны.
							</p>
						</div>
						<span className='rounded-full bg-white px-4 py-2 text-sm font-semibold text-slate-700 shadow-sm'>
							{(joinRequestsPagination?.total ?? joinRequests.length) + uncheckedSubmissionsCount + overdueAssignmentsCount}{' '}
							{hasGlobalAssignmentSummary ? 'в очереди' : 'в очереди (частично)'}
						</span>
					</div>

					<div className='mt-4 grid gap-3 lg:grid-cols-3'>
						{attentionCards.map(card => {
							const toneClass =
								card.tone === 'rose'
									? 'border-rose-200 bg-rose-50 text-rose-700'
									: card.tone === 'amber'
										? 'border-amber-200 bg-amber-50 text-amber-800'
										: card.tone === 'sky'
											? 'border-sky-200 bg-sky-50 text-sky-700'
											: 'border-slate-200 bg-white text-slate-600'
							const icon =
								card.key === 'join-requests' ? (
									<Users className='h-5 w-5' />
								) : card.key === 'submissions' ? (
									<ListChecks className='h-5 w-5' />
								) : (
									<CalendarClock className='h-5 w-5' />
								)
							return (
								<div
									key={card.key}
									className={`rounded-2xl border p-4 ${toneClass}`}
								>
									<div className='flex items-start justify-between gap-3'>
										<div>
											<p className='text-sm font-bold text-slate-900'>
												{card.title}
											</p>
											<p className='mt-2 text-4xl font-black text-slate-900'>
												{card.count}
											</p>
										</div>
										<span className='rounded-full bg-white/80 p-2 shadow-sm'>
											{icon}
										</span>
									</div>
									<p className='mt-3 min-h-[3rem] text-sm leading-6'>
										{card.description}
									</p>
									<a
										href={card.href}
										className='mt-4 inline-flex min-h-10 items-center justify-center rounded-full bg-white px-4 text-sm font-semibold text-slate-700 shadow-sm transition hover:bg-slate-100 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-sky-500'
									>
										{card.action}
									</a>
								</div>
							)
						})}
					</div>

					{joinRequestsError ? (
						<p className='mt-3 rounded-2xl border border-rose-200 bg-white px-4 py-3 text-sm font-semibold text-rose-700'>
							Заявки: {joinRequestsError}
						</p>
					) : null}
				</div>
			</section>
			<section className='teacher-workspace__layout grid gap-6 xl:grid-cols-[minmax(20rem,0.78fr)_minmax(0,1.22fr)]'>
				<section
					id='teacher-classes'
					className='space-y-6 scroll-mt-24'
					aria-labelledby='teacher-classes-title'
				>
					<header className='teacher-workspace__panel codequest-card p-6'>
						<p className='text-sm font-bold uppercase tracking-[0.2em] text-emerald-600'>
							Классы
						</p>
						<h2
							id='teacher-classes-title'
							className='mt-2 text-2xl font-black text-slate-900'
						>
							Классы, ученики и заявки
						</h2>
						<p className='mt-3 text-sm leading-6 text-slate-600'>
							Создавайте классы, выбирайте активный класс, копируйте код и
							принимайте заявки учеников.
						</p>
					</header>
					<form
						onSubmit={createClass}
						className='teacher-workspace__panel codequest-card p-6'
					>
						<p className='text-sm font-bold uppercase tracking-[0.2em] text-emerald-600'>
							Новый класс
						</p>
						<div className='mt-4 space-y-3'>
							<input
								required
								aria-label='Название класса'
								aria-invalid={missingClassFields.includes('name')}
								className={`w-full rounded-2xl border px-4 py-3 ${missingClassFields.includes('name') ? 'border-rose-300 bg-rose-50' : 'border-slate-200'}`}
								placeholder='Название класса'
								value={classForm.name}
								onChange={e =>
									setClassForm({ ...classForm, name: e.target.value })
								}
							/>
							{missingClassFields.includes('name') ? (
								<p className='text-sm font-semibold text-rose-600'>
									Введите название класса.
								</p>
							) : null}
							<textarea
								aria-label='Описание класса'
								className='min-h-28 w-full rounded-2xl border border-slate-200 px-4 py-3'
								placeholder='Описание'
								value={classForm.description}
								onChange={e =>
									setClassForm({ ...classForm, description: e.target.value })
								}
							/>
							<button
								disabled={!canCreateClass}
								className='w-full rounded-full bg-slate-900 px-4 py-2 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:opacity-50 sm:w-auto'
							>
								Создать класс
							</button>
						</div>
					</form>

					<div className='teacher-workspace__panel codequest-card p-6'>
						<div className='flex flex-wrap items-center justify-between gap-3'>
							<p className='text-sm font-bold uppercase tracking-[0.2em] text-emerald-600'>
								Мои классы
							</p>
						</div>
						<div className='mt-4 space-y-3'>
							{overviewLoading ? (
								<EmptyState
									title='Загружаем классы'
									description='Список классов появится здесь после загрузки кабинета.'
								/>
							) : overviewError ? (
								<EmptyState
									title='Классы не загрузились'
									description={overviewError}
									action={
										<button
											type='button'
											onClick={() =>
												loadOverview().catch(() =>
													showErrorToast('Не удалось обновить кабинет.'),
												)
											}
											className='inline-flex min-h-10 items-center justify-center rounded-full bg-slate-900 px-4 text-sm font-semibold text-white'
										>
											Повторить
										</button>
									}
								/>
							) : overview?.classes.length ? (
								classesWindow.visibleItems.map(item => (
								<div
									key={item.id}
									className={`teacher-workspace__item rounded-2xl border px-4 py-4 ${selectedClassId === item.id ? 'border-slate-900 bg-slate-900 text-white' : 'border-slate-200 bg-white text-slate-800'}`}
								>
									<div className='flex flex-wrap items-start justify-between gap-3'>
										<button
											type='button'
											onClick={() => selectClass(item.id)}
											className='min-w-0 flex-1 text-left'
										>
											<p className='break-words text-lg font-black'>
												{item.name}
											</p>
											<p
												className={`mt-2 text-sm ${selectedClassId === item.id ? 'text-slate-300' : 'text-slate-500'}`}
											>
												Код входа:
											</p>
											<p
												className={`break-all font-mono text-sm font-semibold ${selectedClassId === item.id ? 'text-white' : 'text-slate-700'}`}
											>
												{item.code}
											</p>
										</button>
										<div className='flex w-full flex-wrap items-center justify-between gap-2 sm:w-auto sm:justify-end'>
											<span
												className={`rounded-full px-3 py-1 text-xs font-bold ${selectedClassId === item.id ? 'bg-white text-slate-900' : 'bg-sky-50 text-sky-700'}`}
											>
												{item.students_count} учен.
											</span>
											<button
												type='button'
												onClick={() => handleCopyClassCode(item.code)}
												className={`rounded-full px-3 py-2 text-xs font-bold ${selectedClassId === item.id ? 'bg-white text-slate-900' : 'bg-slate-900 text-white'}`}
											>
												Копировать код
											</button>
										</div>
									</div>
								</div>
							))
							) : (
								<EmptyState
									title='Классов пока нет'
									description='Создайте первый класс выше, чтобы получить код входа для учеников.'
									action={
										<button
											type='button'
											onClick={() =>
												document
													.querySelector<HTMLInputElement>(
														'input[placeholder="Название класса"]',
													)
													?.focus()
											}
											className='inline-flex min-h-10 items-center justify-center rounded-full bg-sky-600 px-4 text-sm font-semibold text-white'
										>
											Заполнить название класса
										</button>
									}
								/>
							)}
						</div>
						<FiveItemPager window={classesWindow} loading={overviewLoading} itemLabel='классов' className='mt-4' />
					</div>

					<section className='teacher-workspace__panel codequest-card p-6'>
						<div className='flex flex-wrap items-center justify-between gap-3'>
							<div className='min-w-0'>
								<p className='text-sm font-bold uppercase tracking-[0.2em] text-emerald-600'>
									Заявки на вступление
								</p>
								<h2 className='mt-2 break-words text-2xl font-black text-slate-900'>
									{(joinRequestsPagination?.total ?? joinRequests.length)
										? `${joinRequestsPagination?.total ?? joinRequests.length} ожидают решения`
										: 'Новых заявок нет'}
								</h2>
							</div>
							<button
								type='button'
								onClick={() =>
									loadJoinRequests().catch(() =>
										showErrorToast('Не удалось обновить заявки.'),
									)
								}
								className='rounded-full bg-slate-100 px-4 py-2 text-sm font-semibold text-slate-700'
							>
								Обновить
							</button>
						</div>

						<div className='mt-5 space-y-3'>
							{joinRequestsLoading && joinRequests.length === 0 ? (
								<EmptyState
									title='Загружаем заявки'
									description='Новые заявки учеников появятся здесь после проверки сервера.'
								/>
							) : joinRequestsError ? (
								<EmptyState
									title='Заявки не загрузились'
									description={joinRequestsError}
									action={
										<button
											type='button'
											onClick={() =>
												loadJoinRequests().catch(() =>
													showErrorToast('Не удалось обновить заявки.'),
												)
											}
											className='inline-flex min-h-10 items-center justify-center rounded-full bg-slate-900 px-4 text-sm font-semibold text-white'
										>
											Повторить
										</button>
									}
								/>
							) : joinRequests.length ? (
								requestsWindow.visibleItems.map(joinRequest => (
									<div
										key={joinRequest.id}
										className='teacher-workspace__item rounded-2xl border border-slate-200 bg-slate-50 p-4'
									>
										<div className='flex flex-wrap items-start justify-between gap-3'>
											<div className='min-w-0'>
												<p className='break-words text-lg font-black text-slate-900'>
													{getJoinRequestStudentName(joinRequest)}
												</p>
												<p className='mt-1 text-sm text-slate-500'>
													{joinRequest.classroom_name || 'класс без названия'}
												</p>
												<p className='mt-1 text-xs font-semibold text-slate-500'>
													Отправлена{' '}
													<UserLocalTime
														iso={joinRequest.created_at}
														variant='joinRequest'
														invalidLabel='дата не указана'
													/>
												</p>
											</div>
											<div className='flex w-full flex-wrap gap-2 sm:w-auto sm:justify-end'>
												<button
													type='button'
													onClick={() =>
														setJoinRequestConfirm({
															request: joinRequest,
															action: 'approve',
														})
													}
													className='rounded-full bg-emerald-600 px-4 py-2 text-sm font-semibold text-white'
												>
													Принять
												</button>
												<button
													type='button'
													onClick={() =>
														setJoinRequestConfirm({
															request: joinRequest,
															action: 'reject',
														})
													}
													className='rounded-full bg-white px-4 py-2 text-sm font-semibold text-rose-700 shadow-sm'
												>
													Отклонить
												</button>
											</div>
										</div>
									</div>
								))
							) : (
								<EmptyState
									title='Новых заявок нет'
									description='Когда ученик введет код класса, его заявка появится здесь.'
									action={
										selectedClass ? (
											<button
												type='button'
												onClick={() => handleCopyClassCode(selectedClass.code)}
												className='inline-flex min-h-10 items-center justify-center rounded-full bg-white px-4 text-sm font-semibold text-slate-700 shadow-sm'
											>
												Скопировать код выбранного класса
											</button>
										) : null
									}
								/>
							)}
						</div>
						<FiveItemPager window={requestsWindow} loading={joinRequestsLoading} itemLabel='заявок' className='mt-4' />
					</section>

					<section className='teacher-workspace__panel codequest-card p-6'>
						<div className='flex flex-wrap items-center justify-between gap-3'>
							<div className='min-w-0'>
								<p className='text-sm font-bold uppercase tracking-[0.2em] text-emerald-600'>
									Ученики класса
								</p>
								<h2 className='mt-2 break-words text-2xl font-black text-slate-900'>
									{selectedClass?.name || 'Список появится после выбора класса'}
								</h2>
							</div>
							{selectedClass && (
								<span className='rounded-full bg-slate-100 px-4 py-2 text-sm font-semibold text-slate-700'>
									{classDetail?.students_pagination.total ?? 0} учен.
								</span>
							)}
						</div>
						<p className='mt-3 text-sm leading-6 text-slate-600'>
							{selectedClass
								? 'Быстрый просмотр состава класса и прогресса учеников.'
								: 'Выберите класс выше, чтобы увидеть учеников и их прогресс.'}
						</p>

						<div className='mt-5 space-y-3'>
							{classDetailLoading ? (
								<EmptyState
									title='Загружаем учеников'
									description='Состав выбранного класса появится после загрузки.'
								/>
							) : classDetailError ? (
								<EmptyState
									title='Ученики не загрузились'
									description={classDetailError}
									action={
										selectedClassId ? (
											<button
												type='button'
												onClick={() =>
													loadClassDetails(selectedClassId).catch(() =>
														showErrorToast('Не удалось обновить класс.'),
													)
												}
												className='inline-flex min-h-10 items-center justify-center rounded-full bg-slate-900 px-4 text-sm font-semibold text-white'
											>
												Повторить
											</button>
										) : null
									}
								/>
							) : !selectedClass ? (
								<EmptyState
									title='Класс не выбран'
									description='Выберите класс в списке выше, чтобы увидеть учеников.'
								/>
							) : classDetail?.students.length ? (
								studentsWindow.visibleItems.map(student => (
									<div
										key={student.id}
										className='teacher-workspace__item rounded-2xl border border-slate-200 bg-slate-50 p-4'
									>
										<div className='flex flex-wrap items-start justify-between gap-3'>
											<div>
												<p className='text-lg font-black text-slate-900'>
													{student.full_name}
												</p>
												<p className='text-sm text-slate-500'>
													{student.email}
												</p>
											</div>
											<span className='rounded-full bg-white px-3 py-1 text-xs font-bold text-slate-700'>
												XP {student.xp}
											</span>
										</div>
										<div className='mt-3 flex flex-wrap gap-2 text-xs font-semibold text-slate-600'>
											<span className='rounded-full bg-white px-3 py-1'>
												Уровень {student.level}
											</span>
											<span className='rounded-full bg-white px-3 py-1'>
												Уроков {student.completed_lessons}
											</span>
											<span className='rounded-full bg-white px-3 py-1'>
												Средний балл {student.average_score}%
											</span>
										</div>
									</div>
								))
							) : (
								<EmptyState
									title='В классе пока нет учеников'
									description='Скопируйте код класса и передайте его ученикам, чтобы они отправили заявку.'
									action={
										<button
											type='button'
											onClick={() =>
												selectedClass
													? handleCopyClassCode(selectedClass.code)
													: undefined
											}
											className='inline-flex min-h-10 items-center justify-center rounded-full bg-white px-4 text-sm font-semibold text-slate-700 shadow-sm'
										>
											Скопировать код класса
										</button>
									}
								/>
							)}
						</div>
						<FiveItemPager window={studentsWindow} loading={classDetailLoading} itemLabel='учеников' className='mt-4' />
					</section>
				</section>

				<div className='space-y-6'>
					<section
						id='teacher-lessons'
						className='teacher-workspace__panel codequest-card p-6 scroll-mt-24'
						aria-labelledby='teacher-lessons-title'
					>
						<div className='flex flex-wrap items-center justify-between gap-3'>
							<div>
								<p className='text-sm font-bold uppercase tracking-[0.2em] text-emerald-600'>
									Уроки
								</p>
								<h3
									id='teacher-lessons-title'
									className='mt-2 text-2xl font-black text-slate-900'
								>
									Библиотека + авторские уроки
								</h3>
							</div>
							<div className='flex flex-wrap items-center gap-2'>
								<span className='rounded-full bg-slate-100 px-4 py-2 text-sm font-semibold text-slate-700'>
									{catalogPagination?.total ?? catalog.length} уроков
								</span>
							</div>
						</div>

						<div className='mt-5 grid gap-3 lg:grid-cols-[minmax(0,1fr)_16rem]'>
							<label className='relative block'>
								<span className='sr-only'>Поиск урока</span>
								<Search className='pointer-events-none absolute left-4 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400' />
								<input
									type='search'
									aria-label='Поиск урока'
									value={lessonSearch}
									onChange={event => setLessonSearch(event.target.value)}
									placeholder='Поиск по названию, модулю или описанию'
									className='w-full rounded-2xl border border-slate-200 bg-white py-3 pl-11 pr-4 text-sm text-slate-900 outline-none transition focus:border-sky-400 focus:ring-4 focus:ring-sky-100'
								/>
							</label>
							<label>
								<span className='sr-only'>Источник уроков</span>
								<select
									aria-label='Источник уроков'
									value={lessonSourceFilter}
									onChange={event =>
										setLessonSourceFilter(event.target.value as LessonSourceFilter)
									}
									className='w-full rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm text-slate-900 outline-none transition focus:border-sky-400 focus:ring-4 focus:ring-sky-100'
								>
									{LESSON_SOURCE_FILTER_OPTIONS.map(option => (
										<option key={option.value} value={option.value}>
											{option.label}
										</option>
									))}
								</select>
							</label>
						</div>

						<div className='mt-5 grid gap-3 md:grid-cols-2'>
							{catalogLoading ? (
								<div className='md:col-span-2'>
									<EmptyState
										title='Загружаем уроки'
										description='Библиотека выбранного класса появится здесь.'
									/>
								</div>
							) : catalogError ? (
								<div className='md:col-span-2'>
									<EmptyState
										title='Уроки не загрузились'
										description={catalogError}
										action={
											selectedClassId ? (
												<button
													type='button'
													onClick={() =>
														loadCatalog(selectedClassId).catch(() =>
															showErrorToast('Не удалось обновить уроки.'),
														)
													}
													className='inline-flex min-h-10 items-center justify-center rounded-full bg-slate-900 px-4 text-sm font-semibold text-white'
												>
													Повторить
												</button>
											) : null
										}
									/>
								</div>
							) : !selectedClass ? (
								<div className='md:col-span-2'>
									<EmptyState
										title='Класс не выбран'
										description='Выберите класс, чтобы увидеть каталог и авторские уроки для создания задания.'
									/>
								</div>
							) : catalog.length === 0 ? (
								<div className='md:col-span-2'>
									<EmptyState
										title='Уроков пока нет'
										description='Создайте авторский урок или проверьте доступность каталога для этого класса.'
										action={
											<Link
												href={createLessonHref}
												className='inline-flex min-h-10 items-center justify-center rounded-full bg-sky-600 px-4 text-sm font-semibold text-white'
											>
												Создать урок
											</Link>
										}
									/>
								</div>
							) : filteredLessons.length === 0 ? (
								<div className='md:col-span-2'>
									<EmptyState
										title='По фильтрам ничего не найдено'
										description='Измените поиск или источник, чтобы снова увидеть уроки.'
										action={
											<button
												type='button'
												onClick={() => {
													setLessonSearch('')
													setLessonSourceFilter('all')
												}}
												className='inline-flex min-h-10 items-center justify-center rounded-full bg-white px-4 text-sm font-semibold text-slate-700 shadow-sm'
											>
												Сбросить фильтры
											</button>
										}
									/>
								</div>
							) : (
								catalogWindow.visibleItems.map(lesson => (
								<div
									key={lesson.id}
									className={`teacher-workspace__item rounded-2xl border p-4 ${lesson.source === 'teacher' ? 'border-emerald-200 bg-emerald-50/60' : 'border-slate-200 bg-slate-50'}`}
								>
									<div className='flex flex-wrap items-start justify-between gap-3'>
										<div>
											<p className='text-lg font-black text-slate-900'>
												{lesson.title}
											</p>
											<p className='mt-1 text-sm text-slate-500'>
												{lesson.module_title}
											</p>
										</div>
										<span
											className={`rounded-full px-3 py-1 text-xs font-bold ${lesson.source === 'teacher' ? 'bg-white text-emerald-700' : 'bg-white text-sky-700'}`}
										>
											{lesson.source_label}
										</span>
									</div>
									<p className='mt-3 text-sm leading-6 text-slate-600'>
										{shortenText(lesson.summary, 150)}
									</p>
									<div className='mt-4 flex flex-wrap gap-2'>
										<button
											type='button'
											onClick={() => selectLessonForAssignment(lesson)}
											className='rounded-full bg-slate-900 px-4 py-2 text-sm font-semibold text-white'
										>
											Выбрать для задания
										</button>
										<Link
											href={
												selectedClassId
													? `/teacher/lessons/create?classId=${selectedClassId}&fromLessonId=${lesson.id}`
													: `/teacher/lessons/create?fromLessonId=${lesson.id}`
											}
											className='rounded-full bg-white px-4 py-2 text-sm font-semibold text-slate-700'
										>
											Взять за основу
										</Link>
										{lesson.source === 'teacher' ? (
											<Link
												href={`/teacher/lessons/${lesson.id}/edit`}
												className='rounded-full bg-white px-4 py-2 text-sm font-semibold text-slate-700'
											>
												Редактировать
											</Link>
										) : null}
										<Link
											href={`/lessons/${lesson.id}`}
											className='rounded-full bg-white px-4 py-2 text-sm font-semibold text-slate-700'
										>
											Открыть урок
										</Link>
									</div>
								</div>
							))
							)}
						</div>

						<FiveItemPager window={catalogWindow} loading={catalogLoading} itemLabel='уроков' className='mt-5 rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3' />
					</section>
					<form
						id='teacher-assignments'
						onSubmit={createAssignment}
						className='teacher-workspace__panel codequest-card scroll-mt-24 p-6'
						aria-labelledby='teacher-assignments-title'
					>
						<div className='flex flex-wrap items-center justify-between gap-3'>
							<div>
								<p className='text-sm font-bold uppercase tracking-[0.2em] text-emerald-600'>
									Задания
								</p>
								<h3
									id='teacher-assignments-title'
									className='mt-2 text-2xl font-black text-slate-900'
								>
									Конструктор заданий
								</h3>
							</div>
							<span className='rounded-full bg-emerald-50 px-4 py-2 text-sm font-semibold text-emerald-700'>
								5 блоков: тип → урок → настройки → содержание → критерии
							</span>
						</div>

						<p className='mt-5 text-sm font-bold uppercase tracking-[0.18em] text-slate-500'>
							1. Вид задания
						</p>
						<div className='mt-3 grid gap-3 md:grid-cols-2'>
							{ASSIGNMENT_TYPES.map(type => (
								<button
									key={type}
									type='button'
									onClick={() =>
										setAssignmentForm(current => ({
											...current,
											assignment_type: type,
											submission_format:
												ASSIGNMENT_TEMPLATES[type].submission_format,
										}))
									}
									className={`teacher-workspace__item rounded-2xl border p-4 text-left transition ${assignmentForm.assignment_type === type ? 'border-emerald-500 bg-emerald-50' : 'border-slate-200 bg-white hover:border-slate-300'}`}
								>
									<p className='text-base font-black text-slate-900'>
										{ASSIGNMENT_TEMPLATES[type].label}
									</p>
									<p className='mt-2 text-sm leading-6 text-slate-600'>
										{ASSIGNMENT_TEMPLATES[type].short}
									</p>
								</button>
							))}
						</div>

						<div className='mt-4 rounded-2xl border border-slate-200 bg-slate-50 p-4 text-sm text-slate-600'>
							<p className='font-semibold text-slate-800'>
								Выбран тип:{' '}
								{ASSIGNMENT_TEMPLATES[assignmentForm.assignment_type].label}
							</p>
							<p className='mt-1'>
								Рекомендованный формат сдачи:{' '}
								{SUBMISSION_FORMAT_LABELS[assignmentForm.submission_format]}
							</p>
						</div>
						{!canCreateAssignment ? (
							<div className='mt-4 rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900'>
								{selectedClassId ? (
									<>
										<p>
											До создания задания осталось заполнить:{' '}
											{missingAssignmentFieldLabels.join(', ')}.
										</p>
									</>
								) : (
									<p>Сначала выберите класс, а затем заполните форму задания.</p>
								)}
							</div>
						) : null}

						<p className='mt-6 text-sm font-bold uppercase tracking-[0.18em] text-slate-500'>
							2. Урок
						</p>
						<div className='mt-3 grid gap-3 lg:grid-cols-[minmax(0,0.9fr)_minmax(0,1.1fr)]'>
							<label>
								<span className='text-sm font-semibold text-slate-800'>
									Урок для задания
								</span>
								<select
									required
									aria-invalid={missingAssignmentFields.includes('lesson_id')}
									className={`mt-2 w-full rounded-2xl border px-4 py-3 ${missingAssignmentFields.includes('lesson_id') ? 'border-rose-300 bg-rose-50' : 'border-slate-200'}`}
									value={assignmentForm.lesson_id}
									onChange={e => setAssignmentLesson(e.target.value)}
								>
									<option value=''>Выберите урок для задания</option>
									{selectedLessonForAssignment && !catalogWindow.visibleItems.some(lesson => lesson.id === selectedLessonForAssignment.id) ? (
										<option value={selectedLessonForAssignment.id}>[{selectedLessonForAssignment.source === 'teacher' ? 'Ваш урок' : 'Каталог'}] {selectedLessonForAssignment.title}</option>
									) : null}
									{catalogWindow.visibleItems.map(lesson => (
										<option key={lesson.id} value={lesson.id}>
											[{lesson.source === 'teacher' ? 'Ваш урок' : 'Каталог'}]{' '}
											{lesson.title}
										</option>
									))}
								</select>
								{missingAssignmentFields.includes('lesson_id') ? (
									<FieldError>Выберите урок.</FieldError>
								) : null}
							</label>
							{selectedLessonForAssignment ? (
								<div className='rounded-2xl border border-sky-100 bg-sky-50 p-4 text-sm leading-6 text-slate-700'>
									<p className='text-xs font-bold uppercase tracking-[0.16em] text-sky-700'>
										Выбранный урок
									</p>
									<p className='mt-2 text-base font-black text-slate-900'>
										{selectedLessonForAssignment.title}
									</p>
									<p className='mt-1 text-slate-600'>
										{shortenText(selectedLessonForAssignment.summary, 170)}
									</p>
									<span className='mt-3 inline-flex rounded-full bg-white px-3 py-1 text-xs font-bold text-sky-700'>
										{selectedLessonForAssignment.source_label}
									</span>
								</div>
							) : (
								<EmptyState
									title='Урок не выбран'
									description='Выберите урок из списка или нажмите “Выбрать для задания” в библиотеке выше.'
								/>
							)}
						</div>

						<p className='mt-6 text-sm font-bold uppercase tracking-[0.18em] text-slate-500'>
							3. Дедлайн и настройки
						</p>
						<div className='mt-3 grid gap-3 md:grid-cols-2'>
							<label>
								<span className='text-sm font-semibold text-slate-800'>
									Название задания
								</span>
								<input
									required
									aria-invalid={missingAssignmentFields.includes('title')}
									className={`mt-2 w-full rounded-2xl border px-4 py-3 ${missingAssignmentFields.includes('title') ? 'border-rose-300 bg-rose-50' : 'border-slate-200'}`}
									placeholder='Название задания'
									value={assignmentForm.title}
									onChange={e =>
										setAssignmentForm({
											...assignmentForm,
											title: e.target.value,
										})
									}
								/>
								{missingAssignmentFields.includes('title') ? (
									<FieldError>Введите название задания.</FieldError>
								) : null}
							</label>
							<label>
								<span className='text-sm font-semibold text-slate-800'>
									Дедлайн
								</span>
								<input
									required
									aria-invalid={missingAssignmentFields.includes('due_date')}
									className={`mt-2 w-full rounded-2xl border px-4 py-3 ${missingAssignmentFields.includes('due_date') ? 'border-rose-300 bg-rose-50' : 'border-slate-200'}`}
									type='date'
									value={assignmentForm.due_date}
									onChange={e =>
										setAssignmentForm({
											...assignmentForm,
											due_date: e.target.value,
										})
									}
								/>
								{missingAssignmentFields.includes('due_date') ? (
									<FieldError>Выберите дедлайн.</FieldError>
								) : null}
							</label>
							<label>
								<span className='text-sm font-semibold text-slate-800'>
									Сложность
								</span>
								<select
									aria-label='Сложность задания'
									className='mt-2 w-full rounded-2xl border border-slate-200 px-4 py-3'
									value={assignmentForm.difficulty}
									onChange={e =>
										setAssignmentForm({
											...assignmentForm,
											difficulty: e.target.value as Difficulty,
										})
									}
								>
									<option value='easy'>{DIFFICULTY_LABELS.easy}</option>
									<option value='medium'>{DIFFICULTY_LABELS.medium}</option>
									<option value='hard'>{DIFFICULTY_LABELS.hard}</option>
								</select>
							</label>
							<label>
								<span className='text-sm font-semibold text-slate-800'>
									Формат сдачи
								</span>
								<select
									aria-label='Формат сдачи'
									className='mt-2 w-full rounded-2xl border border-slate-200 px-4 py-3'
									value={assignmentForm.submission_format}
									onChange={e =>
										setAssignmentForm({
											...assignmentForm,
											submission_format: e.target.value as SubmissionFormat,
										})
									}
								>
									{SUBMISSION_FORMAT_OPTIONS.map(item => (
										<option key={item.value} value={item.value}>
											{item.label}
										</option>
									))}
								</select>
							</label>
						</div>
						<p className='mt-3 text-sm text-slate-500'>
							За задания учителя XP не начисляется. Учитель проверяет ответ
							вручную.
						</p>

						<p className='mt-6 text-sm font-bold uppercase tracking-[0.18em] text-slate-500'>
							4. Содержание
						</p>
						<div className='mt-3 grid gap-3 md:grid-cols-2'>
							<label>
								<span className='text-sm font-semibold text-slate-800'>
									Цель обучения
								</span>
								<textarea
									required
									aria-invalid={missingAssignmentFields.includes('learning_goal')}
									className={`mt-2 min-h-24 w-full rounded-2xl border px-4 py-3 ${missingAssignmentFields.includes('learning_goal') ? 'border-rose-300 bg-rose-50' : 'border-slate-200'}`}
									placeholder='Цель обучения'
									value={assignmentForm.learning_goal}
									onChange={e =>
										setAssignmentForm({
											...assignmentForm,
											learning_goal: e.target.value,
										})
									}
								/>
								{missingAssignmentFields.includes('learning_goal') ? (
									<FieldError>Опишите цель обучения.</FieldError>
								) : null}
							</label>
							<label>
								<span className='text-sm font-semibold text-slate-800'>
									Материалы
								</span>
								<textarea
									required
									aria-invalid={missingAssignmentFields.includes('resources')}
									className={`mt-2 min-h-24 w-full rounded-2xl border px-4 py-3 ${missingAssignmentFields.includes('resources') ? 'border-rose-300 bg-rose-50' : 'border-slate-200'}`}
									placeholder='Материалы и ссылки (каждая строка отдельно)'
									value={assignmentForm.resources}
									onChange={e =>
										setAssignmentForm({
											...assignmentForm,
											resources: e.target.value,
										})
									}
								/>
								{missingAssignmentFields.includes('resources') ? (
									<FieldError>Добавьте материалы или ссылки.</FieldError>
								) : null}
							</label>
							<label className='md:col-span-2'>
								<span className='text-sm font-semibold text-slate-800'>
									Описание задания
								</span>
								<textarea
									required
									aria-invalid={missingAssignmentFields.includes('description')}
									className={`mt-2 min-h-28 w-full rounded-2xl border px-4 py-3 ${missingAssignmentFields.includes('description') ? 'border-rose-300 bg-rose-50' : 'border-slate-200'}`}
									placeholder='Описание задания'
									value={assignmentForm.description}
									onChange={e =>
										setAssignmentForm({
											...assignmentForm,
											description: e.target.value,
										})
									}
								/>
								{missingAssignmentFields.includes('description') ? (
									<FieldError>Добавьте описание задания.</FieldError>
								) : null}
							</label>
						</div>

						<p className='mt-6 text-sm font-bold uppercase tracking-[0.18em] text-slate-500'>
							5. Критерии
						</p>
						<div className='mt-3 grid gap-3 md:grid-cols-2'>
							<label>
								<span className='text-sm font-semibold text-slate-800'>
									Шаги выполнения
								</span>
								<textarea
									required
									aria-invalid={missingAssignmentFields.includes('work_steps')}
									className={`mt-2 min-h-28 w-full rounded-2xl border px-4 py-3 ${missingAssignmentFields.includes('work_steps') ? 'border-rose-300 bg-rose-50' : 'border-slate-200'}`}
									placeholder='Каждый шаг с новой строки'
									value={assignmentForm.work_steps}
									onChange={e =>
										setAssignmentForm({
											...assignmentForm,
											work_steps: e.target.value,
										})
									}
								/>
								{missingAssignmentFields.includes('work_steps') ? (
									<FieldError>Добавьте шаги выполнения.</FieldError>
								) : null}
							</label>
							<label>
								<span className='text-sm font-semibold text-slate-800'>
									Критерии успеха
								</span>
								<textarea
									required
									aria-invalid={missingAssignmentFields.includes('success_criteria')}
									className={`mt-2 min-h-28 w-full rounded-2xl border px-4 py-3 ${missingAssignmentFields.includes('success_criteria') ? 'border-rose-300 bg-rose-50' : 'border-slate-200'}`}
									placeholder='Каждый пункт с новой строки'
									value={assignmentForm.success_criteria}
									onChange={e =>
										setAssignmentForm({
											...assignmentForm,
											success_criteria: e.target.value,
										})
									}
								/>
								{missingAssignmentFields.includes('success_criteria') ? (
									<FieldError>Добавьте критерии успеха.</FieldError>
								) : null}
							</label>
						</div>

						<div className='mt-4 flex flex-wrap gap-2'>
							<button
								type='button'
								onClick={() =>
									applyAssignmentTemplate(assignmentForm.assignment_type, true)
								}
								className='rounded-full bg-slate-100 px-4 py-2 text-sm font-semibold text-slate-700'
							>
								Заполнить шаблон под выбранный тип
							</button>
							<button
								type='button'
								onClick={() =>
									applyAssignmentTemplate(assignmentForm.assignment_type)
								}
								className='rounded-full bg-white px-4 py-2 text-sm font-semibold text-slate-700'
							>
								Дополнить пустые поля
							</button>
							<button
								disabled={!canCreateAssignment}
								className='rounded-full bg-sky-600 px-4 py-2 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:opacity-50'
							>
								Добавить задание
							</button>
						</div>
					</form>
				</div>

					<section
						id='teacher-review'
						className='grid min-w-0 gap-5 scroll-mt-24 xl:col-span-2 xl:grid-cols-[minmax(25rem,0.82fr)_minmax(0,1.45fr)] 2xl:grid-cols-[minmax(28rem,0.78fr)_minmax(0,1.55fr)]'
						aria-labelledby='teacher-review-title'
					>
						<div className='teacher-workspace__panel codequest-card min-w-0 p-6 sm:p-7'>
							<div className='flex flex-wrap items-center justify-between gap-3'>
								<div>
									<p className='text-sm font-bold uppercase tracking-[0.2em] text-emerald-600'>
										Задания
									</p>
									<h3 className='mt-2 text-2xl font-black text-slate-900'>
										Задания класса
									</h3>
								</div>
								<span className='rounded-full bg-amber-50 px-4 py-2 text-sm font-semibold text-amber-800'>
									{uncheckedSubmissionsCount} ответов ждут{hasGlobalAssignmentSummary ? '' : ' на странице'}
								</span>
							</div>
							<p className='mt-3 text-sm leading-6 text-slate-600'>
								Сначала показаны задания с непроверенными ответами и истекшими
								дедлайнами.
							</p>
							<div className='mt-5 max-h-[min(78vh,52rem)] min-h-[20rem] space-y-3 overflow-y-auto pr-1'>
								{classDetailLoading ? (
									<EmptyState
										title='Загружаем задания'
										description='Задания выбранного класса появятся здесь.'
										className='min-h-[10rem]'
									/>
								) : classDetailError ? (
									<EmptyState
										title='Задания не загрузились'
										description={classDetailError}
										action={
											selectedClassId ? (
												<button
													type='button'
													onClick={() =>
														loadClassDetails(selectedClassId).catch(() =>
															showErrorToast('Не удалось обновить задания.'),
														)
													}
													className='inline-flex min-h-10 items-center justify-center rounded-full bg-slate-900 px-4 text-sm font-semibold text-white'
												>
													Повторить
												</button>
											) : null
										}
									/>
								) : !selectedClass ? (
									<EmptyState
										title='Класс не выбран'
										description='Выберите класс, чтобы увидеть задания и очередь проверки.'
										className='min-h-[10rem]'
										action={
											<a
												href='#teacher-classes'
												className='inline-flex min-h-10 items-center justify-center rounded-full bg-slate-900 px-4 text-sm font-semibold text-white'
											>
												Выбрать класс
											</a>
										}
									/>
								) : assignmentRows.length === 0 ? (
									<EmptyState
										title='Заданий пока нет'
										description='Создайте первое задание для выбранного класса.'
										className='min-h-[10rem]'
										action={
											<a
												href='#teacher-assignments'
												className='inline-flex min-h-10 items-center justify-center rounded-full bg-sky-600 px-4 text-sm font-semibold text-white'
											>
												К созданию задания
											</a>
										}
									/>
								) : (
									assignmentWindow.visibleItems.map(assignment => {
										const pendingCount = getAssignmentPendingCount(assignment)
										const overdue = isAssignmentOverdue(assignment.due_date)
										return (
											<button
												key={assignment.id}
												type='button'
												onClick={() => selectAssignment(assignment.id)}
												className={`teacher-workspace__item w-full rounded-2xl border px-4 py-4 text-left transition focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-sky-500 ${
													selectedAssignmentId === assignment.id
														? 'border-sky-600 bg-sky-50 shadow-sm'
														: overdue || pendingCount > 0
															? 'border-amber-200 bg-white hover:border-amber-300'
															: 'border-slate-200 bg-white hover:border-slate-300'
												}`}
											>
												<div className='flex flex-wrap items-start justify-between gap-3'>
													<div className='min-w-0'>
														<p className='break-words text-base font-black text-slate-900'>
															{assignment.title}
														</p>
														<p className='mt-1 text-sm text-slate-500'>
															{assignment.assignment_type_label} ·{' '}
															{getDifficultyLabel(assignment.difficulty)} · дедлайн{' '}
															{assignment.due_date || 'без срока'}
														</p>
													</div>
													<div className='flex shrink-0 flex-wrap items-center gap-2'>
														{overdue ? (
															<span className='rounded-full bg-rose-100 px-3 py-1.5 text-xs font-bold text-rose-700'>
																Просрочено
															</span>
														) : null}
														{pendingCount > 0 ? (
															<span className='rounded-full bg-amber-100 px-3 py-1.5 text-xs font-bold text-amber-800'>
																{pendingCount} ждут
															</span>
														) : (
															<span className='rounded-full bg-emerald-50 px-3 py-1.5 text-xs font-bold text-emerald-700'>
							Проверено в списке
															</span>
														)}
														<span className='rounded-full bg-white px-3 py-1.5 text-xs font-bold text-slate-700'>
															{
																SUBMISSION_FORMAT_LABELS[
																	assignment.submission_format
																]
															}
														</span>
													</div>
												</div>
												<div className='mt-2 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs font-semibold'>
													{assignment.lesson ? (
														<span className='text-sky-700'>
															Урок: {assignment.lesson.title}
														</span>
													) : null}
													<span className='text-slate-600'>
														Сдач: {assignment.submissions_count || 0} · Проверено:{' '}
														{assignment.checked_count || 0}
													</span>
												</div>
											</button>
										)
									})
								)}
							</div>
							<FiveItemPager window={assignmentWindow} loading={classDetailLoading} itemLabel='заданий' className='mt-4' />
						</div>

						<div className='teacher-workspace__panel codequest-card min-w-0 p-6 sm:p-7'>
							<div className='flex flex-wrap items-center justify-between gap-3'>
								<div>
									<p className='text-sm font-bold uppercase tracking-[0.2em] text-emerald-600'>
										Проверка
									</p>
									<h3
										id='teacher-review-title'
										className='mt-2 text-2xl font-black text-slate-900'
									>
										Проверка сдач
									</h3>
								</div>
								{selectedAssignment ? (
									<span className='rounded-full bg-slate-100 px-4 py-2 text-sm font-semibold text-slate-700'>
									{submissionsPagination?.total ?? submissions.length} сдач
									</span>
								) : null}
							</div>

							{selectedAssignment ? (
								<div className='mt-5 rounded-2xl border border-slate-200 bg-slate-50 p-4 text-sm leading-6 text-slate-700'>
									<div className='flex flex-wrap items-start justify-between gap-3'>
										<div className='min-w-0'>
											<p className='break-words text-lg font-black leading-6 text-slate-900'>
												{selectedAssignment.title}
											</p>
											<p className='mt-1'>
												{selectedAssignment.assignment_type_label} · дедлайн{' '}
												{selectedAssignment.due_date || 'без срока'}
											</p>
										</div>
										{isAssignmentOverdue(selectedAssignment.due_date) ? (
											<span className='rounded-full bg-rose-100 px-3 py-1.5 text-xs font-bold text-rose-700'>
												Просрочено
											</span>
										) : null}
									</div>
									<div className='mt-4 grid gap-2 sm:grid-cols-3'>
										<div className='rounded-2xl bg-white px-3 py-2'>
											<p className='text-xs font-bold uppercase tracking-[0.12em] text-slate-400'>
												Ждут
											</p>
											<p className='mt-1 text-lg font-black text-slate-900'>
												{getAssignmentPendingCount(selectedAssignment)}
											</p>
										</div>
										<div className='rounded-2xl bg-white px-3 py-2'>
											<p className='text-xs font-bold uppercase tracking-[0.12em] text-slate-400'>
												Проверено
											</p>
											<p className='mt-1 text-lg font-black text-slate-900'>
												{selectedAssignment.checked_count || 0}
											</p>
										</div>
										<div className='rounded-2xl bg-white px-3 py-2'>
											<p className='text-xs font-bold uppercase tracking-[0.12em] text-slate-400'>
												Формат
											</p>
											<p className='mt-1 font-semibold text-slate-700'>
												{
													SUBMISSION_FORMAT_LABELS[
														selectedAssignment.submission_format
													]
												}
											</p>
										</div>
									</div>
								</div>
							) : null}

							<div className='mt-4 flex flex-wrap gap-2'>
								{SUBMISSION_REVIEW_FILTERS.map(filter => (
									<button
										key={filter.value}
										type='button'
										onClick={() => { setSubmissionFilter(filter.value); setSubmissionsPage(1) }}
										className={`rounded-full px-4 py-2 text-sm font-semibold transition ${
											submissionFilter === filter.value
												? 'bg-slate-900 text-white'
												: 'bg-slate-100 text-slate-700 hover:bg-slate-200'
										}`}
									>
										{filter.label}
									</button>
								))}
							</div>

							<div className='mt-5 max-h-[min(78vh,52rem)] min-h-[20rem] space-y-4 overflow-y-auto pr-1'>
								{!selectedAssignmentId ? (
									<EmptyState
										title='Задание не выбрано'
										description='Выберите задание слева, чтобы открыть ответы учеников.'
										className='min-h-[10rem]'
									/>
								) : submissionsLoading ? (
									<EmptyState
										title='Загружаем сдачи'
										description='Ответы учеников появятся здесь после загрузки.'
										className='min-h-[10rem]'
									/>
								) : submissionsError ? (
									<EmptyState
										title='Сдачи не загрузились'
										description={submissionsError}
										action={
											selectedAssignmentId ? (
												<button
													type='button'
													onClick={() =>
														loadSubmissions(selectedAssignmentId).catch(() =>
															showErrorToast('Не удалось обновить сдачи.'),
														)
													}
													className='inline-flex min-h-10 items-center justify-center rounded-full bg-slate-900 px-4 text-sm font-semibold text-white'
												>
													Повторить
												</button>
											) : null
										}
									/>
								) : submissions.length === 0 ? (
									<EmptyState
										title='Сдач пока нет'
										description='Когда ученики отправят ответы, они появятся здесь для проверки.'
										className='min-h-[10rem]'
									/>
								) : filteredSubmissions.length === 0 ? (
									<EmptyState
										title='В этом фильтре пусто'
										description='Переключите статус выше, чтобы увидеть другие сдачи.'
										className='min-h-[10rem]'
									/>
								) : (
									submissionsWindow.visibleItems.map(submission => (
										<div
											key={submission.id}
											className='teacher-workspace__item rounded-2xl border border-slate-200 bg-slate-50 p-5 sm:p-6'
										>
											<div className='flex flex-wrap items-start justify-between gap-3'>
												<div>
													<p className='text-lg font-black text-slate-900'>
														{submission.student_full_name ||
															`Ученик #${submission.student_id}`}
													</p>
													<p className='text-sm text-slate-500'>
														<UserLocalTime
															iso={submission.submitted_at}
															variant='submission'
														/>
													</p>
												</div>
												<div className='grid grid-cols-2 gap-2 text-sm sm:grid-cols-3'>
													<div className='rounded-2xl bg-white px-3 py-2'>
														<p className='text-xs font-bold uppercase tracking-[0.12em] text-slate-400'>
															Статус
														</p>
														<span
															className={`mt-1 inline-flex rounded-full px-2.5 py-1 text-xs font-bold ${getSubmissionStatusClass(submission.status)}`}
														>
															{SUBMISSION_STATUS_LABELS[submission.status]}
														</span>
													</div>
													<div className='rounded-2xl bg-white px-3 py-2'>
														<p className='text-xs font-bold uppercase tracking-[0.12em] text-slate-400'>
															Балл
														</p>
														<p className='mt-1 font-black text-slate-900'>
															{submission.score}%
														</p>
													</div>
													<div className='col-span-2 rounded-2xl bg-white px-3 py-2 sm:col-span-1'>
														<p className='text-xs font-bold uppercase tracking-[0.12em] text-slate-400'>
															Формат
														</p>
														<p className='mt-1 font-semibold text-slate-700'>
															{selectedAssignment
																? SUBMISSION_FORMAT_LABELS[
																		selectedAssignment.submission_format
																	]
																: 'Ответ'}
														</p>
													</div>
												</div>
											</div>
											<div className='mt-4'>
												<p className='text-xs font-bold uppercase tracking-[0.16em] text-slate-500'>
													Ответ ученика
												</p>
												<pre className='mt-2 max-h-[22rem] whitespace-pre-wrap break-words overflow-auto rounded-2xl bg-slate-950 p-4 text-sm leading-6 text-emerald-200'>
													{submission.answer ||
														'Ученик пока не приложил текст ответа.'}
												</pre>
											</div>
											<label className='mt-4 block'>
												<span className='text-xs font-bold uppercase tracking-[0.16em] text-slate-500'>
													Комментарий ученику
												</span>
												<textarea
													aria-label={`Комментарий для ${submission.student_full_name || `ученика ${submission.student_id}`}`}
													value={feedbackDrafts[submission.id] ?? ''}
													onChange={e =>
														setFeedbackDrafts(current => ({
															...current,
															[submission.id]: e.target.value,
														}))
													}
													className='mt-2 min-h-32 w-full rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm leading-6'
													placeholder='Комментарий ученику'
												/>
											</label>
											<div className='mt-3 flex flex-wrap gap-2'>
												<button
													type='button'
													onClick={() =>
														gradeSubmission(
															submission.id,
															'checked',
															submission.score,
															feedbackDrafts[submission.id],
														)
													}
													className='min-h-10 w-full rounded-full bg-emerald-600 px-4 py-2 text-sm font-semibold text-white sm:w-auto'
												>
													Отметить верно
												</button>
												<button
													type='button'
													onClick={() =>
														gradeSubmission(
															submission.id,
															'needs_revision',
															submission.score,
															feedbackDrafts[submission.id],
														)
													}
													className='min-h-10 w-full rounded-full bg-amber-500 px-4 py-2 text-sm font-semibold text-white sm:w-auto'
												>
													Нужна доработка
												</button>
											</div>
										</div>
									))
								)}
							</div>
							<FiveItemPager window={submissionsWindow} loading={submissionsLoading} itemLabel='сдач' className='mt-4' />
						</div>
					</section>
			</section>
			{joinRequestConfirm ? (
				<div
					className='fixed inset-0 z-50 flex items-center justify-center bg-slate-950/50 px-4 py-6 backdrop-blur-sm'
					role='dialog'
					aria-modal='true'
					aria-labelledby='join-request-confirm-title'
				>
					<div className='w-full max-w-md rounded-3xl bg-white p-6 shadow-2xl'>
						<p className='text-sm font-bold uppercase tracking-[0.2em] text-emerald-600'>
							Подтверждение
						</p>
						<h2
							id='join-request-confirm-title'
							className='mt-2 text-2xl font-black text-slate-900'
						>
							{joinRequestConfirm.action === 'approve'
								? 'Принять ученика?'
								: 'Отклонить заявку?'}
						</h2>
						<p className='mt-3 text-sm leading-6 text-slate-600'>
							{joinRequestConfirm.action === 'approve'
								? `Ученик ${getJoinRequestStudentName(joinRequestConfirm.request)} будет добавлен в класс «${joinRequestConfirm.request.classroom_name || 'без названия'}».`
								: `Заявка ученика ${getJoinRequestStudentName(joinRequestConfirm.request)} в класс «${joinRequestConfirm.request.classroom_name || 'без названия'}» будет отклонена.`}
						</p>
						<div className='mt-6 flex flex-col-reverse gap-3 sm:flex-row sm:justify-end'>
							<button
								ref={joinRequestCancelRef}
								type='button'
								onClick={() => setJoinRequestConfirm(null)}
								disabled={joinRequestSubmitting}
								className='rounded-full bg-slate-100 px-5 py-3 text-sm font-semibold text-slate-700 disabled:cursor-not-allowed disabled:opacity-60'
							>
								Отмена
							</button>
							<button
								type='button'
								onClick={confirmJoinRequestDecision}
								disabled={joinRequestSubmitting}
								className={`rounded-full px-5 py-3 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:opacity-60 ${
									joinRequestConfirm.action === 'approve'
										? 'bg-emerald-600'
										: 'bg-rose-600'
								}`}
							>
								{joinRequestSubmitting
									? 'Сохраняем...'
									: joinRequestConfirm.action === 'approve'
										? 'Да, принять'
										: 'Да, отклонить'}
							</button>
						</div>
					</div>
				</div>
			) : null}
		</div>
	)
}
