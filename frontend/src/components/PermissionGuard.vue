<template>
  <slot v-if="hasPermission" />
  <slot v-else name="fallback">
    <el-empty 
      v-if="showEmpty"
      description="暂无权限访问"
      :image-size="200"
    />
  </slot>
</template>

<script setup>
import { computed } from 'vue'
import { usePermissionStore } from '@/stores/permission'

const props = defineProps({
  // 单个权限
  permission: {
    type: String,
    default: ''
  },
  // 多个权限（满足任意一个）
  permissions: {
    type: Array,
    default: () => []
  },
  // 是否需要满足所有权限
  requireAll: {
    type: Boolean,
    default: false
  },
  // 无权限时是否显示空状态
  showEmpty: {
    type: Boolean,
    default: false
  }
})

const permissionStore = usePermissionStore()

const hasPermission = computed(() => {
  // 单个权限检查
  if (props.permission) {
    return permissionStore.can(props.permission)
  }
  
  // 多个权限检查
  if (props.permissions.length > 0) {
    return props.requireAll
      ? permissionStore.canAll(props.permissions)
      : permissionStore.canAny(props.permissions)
  }
  
  // 默认有权限
  return true
})
</script>
