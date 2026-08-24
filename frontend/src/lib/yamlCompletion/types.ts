export type CompletionKind = 'property-key' | 'property-value' | 'array-item'

export interface YamlCompletionContext {
  objectPath: string[]
  insideArrayItem: boolean
  /** Path segment indices that require entering an array item before navigation. */
  arrayItemEnterBefore: number[]
  kind: CompletionKind
  valuePropertyKey?: string
  indentLevel: number
  propertyRowSpaces: number
}

export interface SchemaPathOptions {
  enterArrayItemBefore?: number[]
  enterArrayItemAtEnd?: boolean
}
